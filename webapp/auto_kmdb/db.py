from functools import cache
import mysql.connector
import os
from contextlib import closing
import datetime


connection_pool = mysql.connector.pooling.MySQLConnectionPool(
  pool_name="cnx_pool",
  pool_size=5,
  pool_reset_session=True,
  host=os.environ["MYSQL_HOST"],
  port=os.environ["MYSQL_PORT"],
  user=os.environ["MYSQL_USER"],
  password=os.environ["MYSQL_PASS"],
  database=os.environ["MYSQL_DB"],
)


@cache
def get_all(connection, table, id_column, name_column, limit=300):
    query = f'SELECT {id_column} AS id, {name_column} AS name FROM {table} WHERE status = "Y" LIMIT {limit};'
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return list(cursor.fetchall())


def get_all_persons(connection):
    return get_all(connection, 'news_persons', 'person_id', 'name')


def get_all_institutions(connection):
    return get_all(connection, 'news_institutions', 'institution_id', 'name')


def get_all_places(connection):
    return get_all(connection, 'news_places', 'place_id', 'name_hu')


def get_all_others(connection):
    return get_all(connection, 'news_others', 'other_id', 'name')


def get_all_newspapers(connection):
    return get_all(connection, 'news_newspapers', 'newspaper_id', 'name')


def init_news(connection, source, source_url, clean_url):
    current_datetime = datetime.now()
    with connection.cursor(dictionary=True) as cursor:
        query = """INSERT INTO autokmdb_news
                (source, source_url, clean_url, processing_step, cre_time)
                VALUES (%s, %s, %s, %s)"""
        cursor.execute(query, (0 if source == 'rss' else 1, source_url, clean_url, 0, current_datetime.strftime("%Y-%m-%d %H:%M:%S")))
    connection.commit()


def check_url_exists(connection, url):
    with connection.cursor() as cursor:
        query = "SELECT id FROM autokmdb_news WHERE clean_url = %s"
        cursor.execute(query, (url,))
        results = cursor.fetchall()

        return len(results) != 0


def add_auto_person(connection, autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label):
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_persons 
                (autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label))
    connection.commit()


def add_auto_institution(connection, autokmdb_news_id, institution_id, found_name, found_position, name, classification_score, classification_label):
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_institutions 
                (autokmdb_news_id, institution_id, found_name, found_position, name, classification_score, classification_label) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, institution_id, found_name, found_position, name, classification_score, classification_label))
    connection.commit()


def add_auto_place(connection, autokmdb_news_id, place_id, found_name, found_position, name, classification_score, classification_label):
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_places
                (autokmdb_news_id, place_id, found_name, found_position, name, classification_score, classification_label)
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, place_id, found_name, found_position, name, classification_score, classification_label))
    connection.commit()


def add_auto_other(connection, autokmdb_news_id, other_id, found_name, found_position, name, classification_score, classification_label):
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_others
                (autokmdb_news_id, other_id, found_name, found_position, name, classification_score, classification_label)
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, other_id, found_name, found_position, name, classification_score, classification_label))
    connection.commit()


def save_download_step(connection, id, text, title, description):
    query = '''UPDATE autokmdb_news SET text = %s, title = %s, description = %s, processing_step = 1
               WHERE id = %s;'''
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (text, title, description, id))
    connection.commit()


def skip_same_news(connection, id):
    query = '''UPDATE autokmdb_news SET skip_reason = 2, processing_step = 5
               WHERE id = %s'''
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (id,))
    connection.commit()


def save_classification_step(connection, id, classification_label, classification_score):
    query = '''UPDATE autokmdb_news SET classification_label = %s,
               classification_score = %s, processing_step = 2 WHERE id = %s'''
    with connection.cursor() as cursor:
        cursor.execute(query, (classification_label, classification_score, id))
    connection.commit()


def get_step_queue(connection, step):
    fields = {
        0: 'clean_url AS url',
        1: 'title, description',
        2: 'text',
        3: 'text',
        4: 'text',
    }
    query = f'''SELECT id, {fields[step]} FROM autokmdb_news
               WHERE processing_step = {step} LIMIT 1;'''
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return cursor.fetchone()


def get_download_queue(connection):
    return get_step_queue(connection, 0)


def get_classification_queue(connection):
    return get_step_queue(connection, 1)


def get_ner_queue(connection):
    return get_step_queue(connection, 2)


def get_keyword_queue(connection):
    return get_step_queue(connection, 3)


def get_human_queue(connection):
    return get_step_queue(connection, 4)


def paginate_query(query, page_size, page_number):
    offset = (page_number - 1) * page_size
    return query + f" LIMIT {page_size} OFFSET {offset}"


def get_articles(connection, page, status, domain='mind'):
    query = ''
    if domain == 'mind':
        domain = '%'
    else:
        domain = f"%{domain}%"

    selection = '''SELECT n.id AS id, clean_url AS url, description, title, source, n.classification_score AS classification_score,
            n.text AS text, n.cre_time AS date, GROUP_CONCAT(p.id SEPARATOR ',') AS persons, GROUP_CONCAT(i.id SEPARATOR ',') AS institutions,
            GROUP_CONCAT(pl.id SEPARATOR ',') AS places, GROUP_CONCAT(o.id SEPARATOR ',') AS others
        FROM autokmdb_news n
        LEFT JOIN autokmdb_persons p ON n.id = p.autokmdb_news_id 
        LEFT JOIN autokmdb_institutions i ON n.id = i.autokmdb_news_id 
        LEFT JOIN autokmdb_others o ON n.id = o.autokmdb_news_id 
        LEFT JOIN autokmdb_places pl ON n.id = pl.autokmdb_news_id 
        '''
    group = ' GROUP BY id'

    if status == 'mixed':
        query = '''WHERE n.classification_label = 1 AND processing_step = 3 AND n.annotation_label IS NULL AND clean_url LIKE %s'''
    elif status == 'positive':
        query = '''WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 1 AND clean_url LIKE %s'''
    elif status == 'negative':
        query = '''WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 0 AND clean_url LIKE %s'''
    else:
        print('Invalid status provided!')
        return

    with connection.cursor(dictionary=True) as cursor:
        cursor.execute('SELECT COUNT(id) FROM autokmdb_news n '+query, (domain,))
        count = cursor.fetchone()['COUNT(id)']
        cursor.execute(paginate_query(selection + query + group, 10, page), (domain,))
        return count, cursor.fetchall()


def annote_negative(connection, id):
    query = '''UPDATE autokmdb_news SET annotation_label = 0 WHERE id = %s;'''
    with connection.cursor() as cursor:
        cursor.execute(query, (id,))
    connection.commit()


def save_ner_step(connection, id):
    query = '''UPDATE autokmdb_news SET processing_step = 3 WHERE id = %s;'''
    with connection.cursor() as cursor:
        cursor.execute(query, (id,))
    connection.commit()
