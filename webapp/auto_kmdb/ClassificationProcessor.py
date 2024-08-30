from auto_kmdb.Processor import Processor
from auto_kmdb.db import get_classification_queue, save_classification_step, skip_processing_error
from time import sleep
from transformers import BertForSequenceClassification, BertTokenizer
import torch.nn.functional as F
from auto_kmdb.db import connection_pool
from joblib import load
import torch
import logging
import gc
import traceback
import os


article_classification_prompt = '''{title}
{description}'''

def to_category_id(category):
    if category == 'hungarian-news':
        return 0
    elif category == 'eu-news':
        return 1
    elif category == 'world-news':
        return 2
    return 0

class ClassificationProcessor(Processor):
    def __init__(self):
        #super().__init__()
        logging.info('initialized classification processor')
        self.done = False

    def is_done(self):
        return self.done

    def load_model(self):
        logging.info('loading classification model')
        self.model = BertForSequenceClassification.from_pretrained(
            'K-Monitor/kmdb_classification_hubert')
        self.tokenizer = BertTokenizer.from_pretrained('SZTAKI-HLT/hubert-base-cc', max_length=512)
        self.svm_classifier = load('data/svm_classifier_category.joblib')
        self.is_done = True
        logging.info('loaded classification model')

    def predict(self):
        logging.info('running classification prediction')
        with torch.no_grad():
            inputs = self.tokenizer(self.text, return_tensors="pt")
            self.output = self.model(**inputs, output_hidden_states=True)
            cls_embedding = self.output.hidden_states[-1][:, 0, :].squeeze().numpy()

            logits = self.output.logits
            probabilities = F.softmax(logits[0], dim=-1)
            self.score = float(probabilities[1])
            self.label = 1 if self.score > 0.42 else 0

            self.category = to_category_id(self.svm_classifier.predict([cls_embedding])[0])
            del inputs, logits, probabilities

    def process_next(self):
        with connection_pool.get_connection() as connection:
            next_row = get_classification_queue(connection)
        if next_row is None:
            sleep(30)
            return
        logging.info('processing next classification')
        
        self.text = article_classification_prompt.format(title=next_row['title'], description=next_row['description'])
        self.article_text = next_row['text']

        try:
            self.predict()
            if next_row['source'] == 1:
                with connection_pool.get_connection() as connection:
                    save_classification_step(connection, next_row['id'], 1, 1.0, self.category)
            else:
                with connection_pool.get_connection() as connection:
                    save_classification_step(connection, next_row['id'], self.label, self.score, self.category)
            del self.output
        except Exception as e:
            with connection_pool.get_connection() as connection:
                skip_processing_error(connection, next_row["id"])
            logging.warn('exception during: '+str(next_row["id"]))
            logging.error(e)
            print(traceback.format_exc())
            logging.error(traceback.format_exc())

        torch.cuda.empty_cache()
        gc.collect()
