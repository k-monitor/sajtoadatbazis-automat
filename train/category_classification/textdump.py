import mysql.connector
import jsonlines
import os

# Connect to MySQL database
mysql_db = mysql.connector.connect(
  host=os.environ["MYSQL_HOST"],
  port=os.environ["MYSQL_PORT"],
  user=os.environ["MYSQL_USER"],
  password=os.environ["MYSQL_PASS"],
  database=os.environ["MYSQL_DB"],
)

# Create a cursor object
with mysql_db.cursor(dictionary=True) as cursor, jsonlines.open('texts.jsonl', 'w') as writer:
    cursor.execute('SET SESSION group_concat_max_len = 10000;')
    query = """
    SELECT n.news_id, nl.articletext AS text
    FROM news_news n
    JOIN news_lang nl ON n.news_id = nl.news_id
    GROUP BY n.news_id;
    """
    # LIMIT 10;
    cursor.execute(query)
    rows = cursor.fetchall()
    writer.write_all(rows)
