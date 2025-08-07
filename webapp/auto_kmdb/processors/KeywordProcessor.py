from auto_kmdb.processors import Processor
from time import sleep
from auto_kmdb import db
import logging
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.preprocessing import normalize
from sklearn.feature_extraction.text import TfidfTransformer, CountVectorizer

other_name_to_id = {other["name"]: other["id"] for other in db.get_all_others() if other["name"]}
file_name_to_id = {file["name"]: file["id"] for file in db.get_all_files() if file["name"]}

class CTFIDFVectorizer(TfidfTransformer):
    def __init__(self, *args, **kwargs):
        super(CTFIDFVectorizer, self).__init__(*args, **kwargs)

    def fit(self, X: sp.csr_matrix, n_samples: int):
        """Learn the idf vector (global term weights)"""
        _, n_features = X.shape
        df = np.squeeze(np.asarray(X.sum(axis=0)))
        idf = np.log(n_samples / df)
        self._idf_diag = sp.diags(
            idf,
            offsets=0,
            shape=(n_features, n_features),
            format="csr",
            dtype=np.float64,
        )
        return self

    def transform(self, X: sp.csr_matrix) -> sp.csr_matrix:
        """Transform a count-based matrix to c-TF-IDF"""
        X = X * self._idf_diag
        X = normalize(X, axis=1, norm="l1", copy=False)
        return X


class CTFIDFClassifier:
    def __init__(self, class_name="others"):
        if class_name == "others":
            names = other_name_to_id.keys()
        elif class_name == "files":
            names = file_name_to_id.keys()
        from datasets import load_dataset
        from nltk.corpus import stopwords
        from nltk.stem import SnowballStemmer
        from sklearn.metrics.pairwise import cosine_similarity

        self.stemmer = SnowballStemmer("hungarian")
        self.hungarian_stopwords = stopwords.words("hungarian")

        # Load and prepare dataset
        ds = load_dataset("K-Monitor/kmdb_base")
        ds = ds.filter(lambda x: x["text"] and x[class_name])

        ds = ds["train"].map(
            lambda x: {"text": (x["text"])},
        )

        text_by_articles = [
            {other: article["text"] for other in article[class_name] if other in names} for article in ds
        ]

        documents = []
        for article in text_by_articles:
            for other, text in article.items():
                if text and other:
                    documents.append((other, text))

        target, data = zip(*documents)

        # Get train data
        docs = pd.DataFrame({"Document": data, "Class": target})
        self.docs_per_class = docs.groupby(["Class"], as_index=False).agg(
            {"Document": " ".join}
        )

        # Create c-TF-IDF based on the train data
        self.count_vectorizer = CountVectorizer(
            stop_words=self.hungarian_stopwords
        ).fit(self.docs_per_class.Document)
        count = self.count_vectorizer.transform(self.docs_per_class.Document)
        self.ctfidf_vectorizer = CTFIDFVectorizer().fit(count, n_samples=len(docs))
        self.ctfidf = self.ctfidf_vectorizer.transform(count)

    def stem(self, text):
        """Stem text."""
        words = text.lower().split()
        return " ".join([self.stemmer.stem(word) for word in words])

    def predict(self, text):
        """Predict class for given text."""
        from sklearn.metrics.pairwise import cosine_similarity

        count = self.count_vectorizer.transform([text])
        vector = self.ctfidf_vectorizer.transform(count)
        distances = cosine_similarity(vector, self.ctfidf)[0]

        def softmax(x, temp):
            return np.exp(np.divide(x, temp)) / np.sum(
                np.exp(np.divide(x, temp)), axis=0
            )

        indexed_distances = list(enumerate(distances))
        indexed_distances.sort(key=lambda x: x[1], reverse=True)
        predictions = indexed_distances[:5]
        top5_indexes, top5_distances = zip(*predictions)
        predictions = [
            (self.docs_per_class.Class[i], top5_distances[j])
            for j, i in enumerate(top5_indexes)
        ]

        return predictions


class KeywordProcessor(Processor):
    def __init__(self):
        # super().__init__()
        logging.info("initialized keyword processor")
        self.done = False

    def load_model(self):
        self.others_classifier = CTFIDFClassifier(class_name="others")
        self.files_classifier = CTFIDFClassifier(class_name="files")
        self.done = True

    def is_done(self):
        return self.done

    def predict_others(self, text):
        """Predict keywords for the next article."""
        return self.others_classifier.predict(text)
    
    def predict_files(self, text):
        """Predict files for the next article."""
        return self.files_classifier.predict(text)

    def process_next(self):
        with db.connection_pool.get_connection() as connection:
            next_rows: list = db.get_keyword_queue(connection)
        for next_row in next_rows:
            if next_row is None:
                sleep(30)
                return
            text = next_row["text"]
            others = self.predict_others(text)
            files = self.predict_files(text)

            with db.connection_pool.get_connection() as connection:
                for other_name, classification_score in others:
                    other_id = other_name_to_id.get(other_name, None)
                    if other_id is None:
                        logging.warning(
                            f"KeywordProcessor: {other_name} not found in others table"
                        )
                        continue
                    db.add_auto_other(
                        connection,
                        next_row["id"],
                        other_id,
                        other_name,
                        float(classification_score),
                        1,
                    )
                for file_name, classification_score in files:
                    file_id = file_name_to_id.get(file_name, None)
                    if file_id is None:
                        logging.warning(
                            f"KeywordProcessor: {file_name} not found in files table"
                        )
                        continue
                    db.add_auto_files(
                        connection,
                        next_row["id"],
                        file_id,
                        file_name,
                        float(classification_score),
                        1,
                    )
                db.save_keyword_step(connection, next_row["id"])
