import mysql.connector
import os
from dotenv import load_dotenv
import jsonlines

load_dotenv('../../.env.prod')

mysql_db = mysql.connector.connect(
  host=os.environ["MYSQL_HOST"],
  port=os.environ["MYSQL_PORT"],
  user=os.environ["MYSQL_USER"],
  password=os.environ["MYSQL_PASS"],
  database=os.environ["MYSQL_DB"],
)

with mysql_db.cursor(dictionary=True) as cursor, jsonlines.open('urls.jsonl', 'w') as writer:
    query = '''
SELECT news_id, source_url
FROM news_news
WHERE cre_time > 1696069407'''
    cursor.execute(query)
    rows = cursor.fetchall()
    print(len(rows))
    writer.write_all(rows)
