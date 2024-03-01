from flask_sqlalchemy import SQLAlchemy
import mysql.connector
import os

db = SQLAlchemy()

mysql_db = mysql.connector.connect(
  host=os.environ["MYSQL_HOST"],
  port=os.environ["MYSQL_PORT"],
  user=os.environ["MYSQL_USER"],
  password=os.environ["MYSQL_PASS"],
  database=os.environ["MYSQL_DB"],
)


def get_all_persons():
    with mysql_db.cursor(dictionary=True) as cursor:
        cursor.execute('SELECT person_id AS id, name FROM news_persons WHERE status = "Y" LIMIT 3;')
        return list(cursor.fetchall())

def get_all_institutions():
    with mysql_db.cursor(dictionary=True) as cursor:
        cursor.execute('SELECT institution_id AS id, name FROM news_institutions WHERE status = "Y" LIMIT 3;')
        return list(cursor.fetchall())

def get_all_places():
    with mysql_db.cursor(dictionary=True) as cursor:
        cursor.execute('SELECT place_id AS id, name_hu FROM news_places WHERE status = "Y" LIMIT 3;')
        return list(cursor.fetchall())

def get_all_others():
    with mysql_db.cursor(dictionary=True) as cursor:
        cursor.execute('SELECT other_id AS id, name FROM news_others WHERE status = "Y" LIMIT 3;')
        return list(cursor.fetchall())

def get_all_newspapers():
    with mysql_db.cursor(dictionary=True) as cursor:
        cursor.execute('SELECT newspaper_id AS id, name FROM news_newspapers WHERE status = "Y" LIMIT 3;')
        return list(cursor.fetchall())

