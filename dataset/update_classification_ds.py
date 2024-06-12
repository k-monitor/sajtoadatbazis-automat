import mysql.connector
import os
from datasets import load_dataset, Dataset, concatenate_datasets
from dotenv import load_dotenv
load_dotenv()

dataset = load_dataset("boapps/kmdb_classification")
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
SELECT text, title, description, annotation_label AS label, clean_url as url
FROM autokmdb_news
WHERE annotation_label = 0
ORDER BY id;'''
    cursor.execute(query)
    rows = cursor.fetchall()
    print(len(rows))

    negative_ds = Dataset.from_list(rows).map(lambda row: {'keywords': [''], 'is_hand_annoted': True, 'score': None, 'title_score': None, 'date': None})  # row['date'].strftime('%Y-%m-%d %H:%M:%S')
    print(negative_ds[0])
    print(dataset)
    dataset['train'] = concatenate_datasets([dataset['train'], negative_ds])
    print(dataset)

    # dataset.push_to_hub("K-Monitor/kmdb_classification")
