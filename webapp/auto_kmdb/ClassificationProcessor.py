from auto_kmdb.Processor import Processor
from auto_kmdb.db import get_classification_queue, save_classification_step
from time import sleep
from transformers import BertForSequenceClassification, BertTokenizer
import torch.nn.functional as F
from auto_kmdb.db import connection_pool


article_classification_prompt = '''{title}
{description}'''


class ClassificationProcessor(Processor):
    def __init__(self):
        #super().__init__()
        self.done = False

    def is_done(self):
        return self.done

    def load_model(self):
        self.model = BertForSequenceClassification.from_pretrained(
            'boapps/kmdb_classification_model')
        self.tokenizer = BertTokenizer.from_pretrained('SZTAKI-HLT/hubert-base-cc', max_length=512)
        self.is_done = True
        print('Class model loaded')

    def predict(self):
        inputs = self.tokenizer(self.text, return_tensors="pt")
        logits = self.model(**inputs).logits
        probabilities = F.softmax(logits[0], dim=-1)
        self.score = float(probabilities[1])
        self.label = 1 if self.score > 0.42 else 0
        print(self.score)

    def process_next(self):
        with connection_pool.get_connection() as connection:
            next_row = get_classification_queue(connection)
        if next_row is None:
            sleep(30)
            return
        
        if next_row['source'] == 1:
            with connection_pool.get_connection() as connection:
                save_classification_step(connection, next_row['id'], 1, 1.0)
            return

        self.text = article_classification_prompt.format(title=next_row['title'], description=next_row['description'])

        self.predict()

        with connection_pool.get_connection() as connection:
            save_classification_step(connection, next_row['id'], self.label, self.score)
