from os import environ
from typing import Any
from numpy import ndarray
from sklearn.svm import SVC
from transformers.tokenization_utils_base import BatchEncoding
from huggingface_hub import hf_hub_download
from auto_kmdb.processors import Processor
from time import sleep
from transformers import (
    BertForSequenceClassification,
    BertTokenizer,
    PreTrainedTokenizer,
    PreTrainedModel,
)
import torch.nn.functional as F
from auto_kmdb import db
from joblib import load
import torch
import logging
import gc
import traceback
from chromadb import (
    Documents,
    EmbeddingFunction,
    Embeddings,
    PersistentClient,
    Collection,
    QueryResult,
)
import numpy as np
from datetime import datetime
from google import genai
from google.genai import types
from google.genai.types import GenerateContentResponse

USE_GEMINI = environ.get("USE_GEMINI", "false").lower() == "true"
SIMILARITY_THRESHOLD = 0.7
GEMINI_MODEL = environ.get("GEMINI_MODEL", "gemini-2.5-flash-preview-04-17")


def genai_label(title, description, text):
    client = genai.Client(
        api_key=environ.get("GEMINI_API_KEY"),
    )
    model = GEMINI_MODEL
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"""A köetkező a K-Monitor sajtóadatbázisának módszertana, ami alapján majd egy cikkről el kell döntened, hogy illik-e az adatbázisba:

# **Sajtóadatbázis módszertan**

Adatbázisunk ([adatbazis.k-monitor.hu](https://adatbazis.k-monitor.hu/)) könyvtárszerűen gyűjti össze a magyar online-sajtó **korrupcióról**, **közbeszerzésekről**, **közpénzfelhasználásról**, illetve általában a **közélet tisztaságáról**, **átláthatóságáról** szóló, és a konkrét ügyeket, eseteket leíró cikkekre vonatkozó adatokat, melyeket állandó, szigorú módszertan szerint válogatunk és címkézünk.  
A Sajtóadatbázist 2023-ban közel 450.000 felhasználó látogatta.

# **A címkézés alapelve**

A címkézés célja, hogy az adott cikk a K-Monitor saját, illetve a világháló keresőmotorjai által könnyen megtalálható legyen. Cél: aki felmegy az adatbázisra és adott személyről, intézményről, témakörben keres, az találja meg a korábbi történeteket.

# **Felhasználói fiók**

- Regisztrációdat egy K-Monitor munkatársunk tudja létrehozni és beállítani a hozzá kapcsolódó szükséges hozzáféréseket.  
- Ha ez megtörtént, itt tudsz belépni: [https://adatbazis.k-monitor.hu/admin.php](https://adatbazis.k-monitor.hu/admin.php)

# **A cikkek kiválasztásának szempontjai**

1. **Konkrét** korrupciós esetet ír le (*Tibi bácsi megvesztegette a záhonyi vámosokat*).  
2. A **cikk** **szerzője állítja, vagy sugallja**, hogy valaki a ráruházott hatalmat saját maga, vagy egy harmadik fél hasznára fordította (*polgármester a józan ésszel beláthatónál jóval drágábban vásárolt traktort a falunak*).  
3. A cikk korrupciós ügyben történő **jogi eljárásról** tájékoztat (*vádat emeltek xy képviselővel szemben hűtlen kezelés ügyében*).  
4. Egy korrupciós **vádat cáfolnak** vagy védekeznek (*én, Tóbiás Szilamér, nem is vagyok korrupt*).  
5. A következő **témák esetében szabálytalanságok** merülnek fel: közbeszerzés, pártfinanszírozás, pályázatok, kormányzati szerv vagy állami vállalat gazdálkodása, vagyonosodás, juttatások, privatizáció, whistleblowing.   
6. A következő **kifejezések** közül valamelyik előfordul a cikkben: korrupció, sikkasztás (közszolga által), hűtlen kezelés, vesztegetés, hivatali visszaélés, hatalommal való visszaélés, befolyással üzérkedés, hanyagság, adócsalás, számviteli fegyelem megsértése, protekció, nepotizmus, jogosulatlan gazdasági előny, versenykorlátozás, kartell, whistleblowing/közérdekű bejelentés, közérdekű adatok, átláthatóság.

**Nem kell felvinni**:

* pártközlemény  
* publicisztika  
* random mocskolódás (*Matolcsy egy korrupt őrült*)  
* ha nem saját anyag, hanem más lapra hivatkozik (*... írja az Index*) **és** nincs hozzáadott információ


Ez volt a módszertan, most következik a cikk, amiről döntened kell:

{title}

{description}

{text}

Ez volt a cikk, most dönts, hogy illik-e az adatbázisba, a választ sima json formátumban add meg! Ha illik, akkor a label értéke legyen true, ha pedig nem, akkor false."""
                ),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=0,
        thinking_config=types.ThinkingConfig(
            thinking_budget=100,
        ),
        response_mime_type="application/json",
        response_schema=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["label"],
            properties={
                "label": genai.types.Schema(
                    type=genai.types.Type.BOOLEAN,
                ),
            },
        ),
    )
    response: GenerateContentResponse = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )

    token_counts = {
        "prompt": response.usage_metadata.prompt_token_count,
        "response": response.usage_metadata.candidates_token_count,
        "thinking": response.usage_metadata.thoughts_token_count,
    }

    return response.parsed["label"], token_counts


class MyEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return [parse_embedding(text) for text in input]


def parse_embedding(embedding: str) -> ndarray:
    return np.array([float(x) for x in embedding.split(",")])


def encode_embedding(embedding: ndarray) -> str:
    return ",".join(str(x) for x in embedding)


def find_similar(embedding: ndarray, collection: Collection, domain: str):
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    qfilter = (
        {"$and": [{"date": {"$eq": date}}, {"domain": {"$ne": domain}}]}
        if domain
        else {"date": {"$eq": date}}
    )
    result: QueryResult = collection.query([embedding], n_results=10, where=qfilter)
    if not result or not result["distances"]:
        return None
    return list(zip(result["ids"][0], result["distances"][0]))


chroma_client = PersistentClient(path="data/chroma.db")

chroma_collection = chroma_client.get_or_create_collection(
    name="my_collection",
    embedding_function=MyEmbeddingFunction(),
)

logging.info("ChromaDB collection created")

CATEGORY_MAP: dict[str, int] = {"hungarian-news": 0, "eu-news": 1, "world-news": 2}


def format_article(title, description, url):
    domain = ".".join(url.split("/")[2].split(".")[-2:])
    return f"{title}\n{description}\n({domain})"


class ClassificationProcessor(Processor):
    def __init__(self) -> None:
        logging.info("Initializing classification processor")
        self.done: bool = False
        self.model: PreTrainedModel
        self.tokenizer: PreTrainedTokenizer
        self.svm_classifier: SVC

    def is_done(self) -> bool:
        return self.done

    def load_model(self) -> None:
        logging.info("Loading classification model")
        self.model = BertForSequenceClassification.from_pretrained(
            "K-Monitor/kmdb_classification_hubert_v2"
        ).to(environ.get("DEVICE", "cpu"))
        self.tokenizer = BertTokenizer.from_pretrained(
            "SZTAKI-HLT/hubert-base-cc", max_length=512
        )
        self.svm_classifier = load(
            hf_hub_download(
                repo_id="K-Monitor/kmdb_classification_category_v2",
                filename="svm_classifier_category.joblib",
            )
        )
        self.done = True
        logging.info("Classification model loaded")

    def _prepare_input(self, text) -> BatchEncoding:
        """Prepares the input for prediction."""
        return self.tokenizer(text, return_tensors="pt")

    def _extract_outputs(self, inputs) -> tuple[ndarray, ndarray]:
        """Extracts logits and CLS embedding from model outputs."""
        output = self.model(**inputs, output_hidden_states=True)
        cls_embedding: ndarray = (
            output.hidden_states[-1][:, 0, :].squeeze().cpu().numpy()
        )
        return output.logits, cls_embedding

    def predict(
        self, title: str, description: str, text: str, url: str
    ) -> tuple[int, float, int, str]:
        logging.info("Running classification prediction")
        prediction_text: str = format_article(title, description, url)
        inputs = self._prepare_input(prediction_text).to(environ.get("DEVICE", "cpu"))

        score: float
        label: int
        category: int
        str_embedding: Optional[str] = None
        with torch.no_grad():
            logits, cls_embedding = self._extract_outputs(inputs)

            probabilities = F.softmax(logits[0], dim=-1)
            score = float(probabilities[1])
            label = 1 if score > 0.42 else 0
            if label == 1 and USE_GEMINI:
                google_label, token_counts = genai_label(title, description, text)
                if google_label:
                    label = 1
                else:
                    label = 0
            if label == 1:
                str_embedding = encode_embedding(cls_embedding)
            category = CATEGORY_MAP.get(
                self.svm_classifier.predict([cls_embedding])[0], 0
            )

        del inputs, logits, probabilities
        return label, score, category, str_embedding

    def _save_classification(self, connection, next_row, label, score, category):
        """Saves the classification result to the database."""
        if next_row["source"] == 1:
            db.save_classification_step(connection, next_row["id"], 1, 1.0, category)
        else:
            db.save_classification_step(
                connection, next_row["id"], label, score, category
            )

    def process_next(self):
        with db.connection_pool.get_connection() as connection:
            next_rows = db.get_classification_queue(connection)

        for next_row in next_rows:
            if next_row is None:
                sleep(30)
                return
            autokmdb_id = next_row["id"]

            logging.info("Processing next classification")

            try:
                label, score, category, str_embedding = self.predict(
                    next_row["title"],
                    next_row["description"],
                    next_row["text"],
                    next_row["clean_url"],
                )
                domain = ".".join(next_row["clean_url"].split("/")[2].split(".")[-2:])
                if label == 1:
                    cls_embedding = parse_embedding(str_embedding)
                    similar_result = find_similar(
                        cls_embedding, chroma_collection, domain
                    )
                    good_results = (
                        [
                            (article_id, distance)
                            for article_id, distance in similar_result
                            if distance < SIMILARITY_THRESHOLD * 100
                        ]
                        if similar_result
                        else []
                    )
                    good_results = sorted(
                        good_results, key=lambda x: x[1], reverse=False
                    )
                    logging.info(
                        f"Found similar articles: {good_results} to {autokmdb_id}"
                    )
                    print(f"Found similar articles: {good_results} to {autokmdb_id}")
                    # autokmdb_id: new article
                    # article_id: similar article
                    for article_id, distance in good_results:
                        with db.connection_pool.get_connection() as connection:
                            group_id = db.find_group_by_autokmdb_id(
                                connection, article_id
                            )
                            if group_id:
                                db.add_article_to_group(
                                    connection, autokmdb_id, group_id
                                )
                            else:
                                db.add_article_group(connection, article_id)
                                group_id = db.find_group_by_autokmdb_id(
                                    connection, article_id
                                )
                                db.add_article_to_group(
                                    connection, autokmdb_id, group_id
                                )
                        break  # temporary solution
                    now = datetime.now()
                    date = now.strftime("%Y-%m-%d")
                    chroma_collection.add(
                        documents=[str_embedding],
                        ids=[str(autokmdb_id)],
                        metadatas=[
                            {
                                "date": date,
                                "domain": domain,
                            }
                        ],
                    )

                with db.connection_pool.get_connection() as connection:
                    self._save_classification(
                        connection, next_row, label, score, category
                    )
            except Exception as e:
                with db.connection_pool.get_connection() as connection:
                    db.skip_processing_error(connection, autokmdb_id)

                logging.warning(f"Exception during: {autokmdb_id}")
                logging.error(e)
                logging.error(traceback.format_exc())

        torch.cuda.empty_cache()
        gc.collect()
