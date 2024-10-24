import mysql.connector
import os
from datasets import load_dataset, Dataset, concatenate_datasets
from dotenv import load_dotenv
import random
load_dotenv('../../webapp/.env.prod')
random.seed = 42

def filter_list_end_biased(input_list, min_prob=0.3, max_prob=1.0):
    list_length = len(input_list)
    
    def get_probability(index):
        return min_prob + (max_prob - min_prob) * (index / (list_length - 1))
    
    return [item for index, item in enumerate(input_list) if random.random() < get_probability(index)]

positive_dataset = Dataset.from_list(filter_list_end_biased(load_dataset("K-Monitor/kmdb_base").remove_columns(['news_id', 'archive_url', 'kmdb_url', 'category', 'files', 'persons', 'institutions', 'places', 'others']).rename_column('source_url', 'url').rename_column('pub_time', 'date').map(lambda row: {'label': 1, 'is_hand_annoted': True})['train']))
dataset = load_dataset("boapps/kmdb_classification")
dataset = dataset.filter(lambda row: row['label'] == 0)

mysql_db = mysql.connector.connect(
  host=os.environ["MYSQL_HOST"],
  port=os.environ["MYSQL_PORT"],
  user=os.environ["MYSQL_USER"],
  password=os.environ["MYSQL_PASS"],
  database=os.environ["MYSQL_DB"],
)

print(sorted(dataset['train'].filter(lambda row: row['date'])['date'])[-1])
print(sorted(dataset['test'].filter(lambda row: row['date'])['date'])[-1])
print(sorted(dataset['validation'].filter(lambda row: row['date'])['date'])[-1])

with mysql_db.cursor(dictionary=True) as cursor:
    query = '''
SELECT text, title, newspaper_name as newspaper, description, annotation_label AS label, clean_url as url
FROM autokmdb_news
WHERE annotation_label = 0 AND negative_reason = 0
ORDER BY id;'''
    cursor.execute(query)
    rows = cursor.fetchall()
    print(len(rows))

negative_ds_prod = Dataset.from_list(rows).map(lambda row: {'keywords': [''], 'is_hand_annoted': True, 'score': None, 'title_score': None, 'date': None})  # row['date'].strftime('%Y-%m-%d %H:%M:%S')

load_dotenv('../../webapp/.env')


mysql_db = mysql.connector.connect(
  host=os.environ["MYSQL_HOST"],
  port=os.environ["MYSQL_PORT"],
  user=os.environ["MYSQL_USER"],
  password=os.environ["MYSQL_PASS"],
  database=os.environ["MYSQL_DB"],
)

with mysql_db.cursor(dictionary=True) as cursor:
    query = '''
SELECT text, title, newspaper_name as newspaper, description, annotation_label AS label, clean_url as url
FROM autokmdb_news
WHERE annotation_label = 0 AND negative_reason = 0
ORDER BY id;'''
    cursor.execute(query)
    rows = cursor.fetchall()
    print(len(rows))


negative_ds = Dataset.from_list(rows).map(lambda row: {'keywords': [''], 'is_hand_annoted': True, 'score': None, 'title_score': None, 'date': None})  # row['date'].strftime('%Y-%m-%d %H:%M:%S')
print(negative_ds[0])
print(dataset)
dataset = concatenate_datasets([dataset['train'], dataset['validation'], dataset['test'], negative_ds, negative_ds_prod, positive_dataset])
# dataset = dataset.remove_columns(['title_score', 'score'])
print(dataset)
print(dataset.filter(lambda row: row['label'] == 0))
print(dataset.filter(lambda row: row['label'] == 1))

dataset.push_to_hub("K-Monitor/kmdb_classification")
