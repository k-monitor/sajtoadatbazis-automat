from functools import cache
import mysql.connector
import os
from contextlib import closing
from datetime import datetime

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
def get_all(connection, table, id_column, name_column):
    query = f'SELECT {id_column} AS id, {name_column} AS name FROM {table} WHERE status = "Y";'
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


def init_news(connection, source, source_url, clean_url, newspaper_name, newspaper_id):
    current_datetime = datetime.now()
    cre_time = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    with connection.cursor(dictionary=True) as cursor:
        query = """INSERT INTO autokmdb_news
                (source, source_url, clean_url, processing_step, cre_time, newspaper_name, newspaper_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (0 if source == 'rss' else 1, source_url, clean_url, 0, cre_time, newspaper_name, newspaper_id))
    connection.commit()


def check_url_exists(connection, url):
    with connection.cursor() as cursor:
        query = "SELECT id FROM autokmdb_news WHERE clean_url = %s"
        cursor.execute(query, (url,))
        results = cursor.fetchall()

        return len(results) != 0


def add_auto_person(connection, autokmdb_news_id, person_name, person_id, found_name, found_position, name, classification_score, classification_label):
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_persons
                (autokmdb_news_id, person_name, person_id, found_name, found_position, name, classification_score, classification_label)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, person_name, person_id, found_name, found_position, name, classification_score, classification_label))
    connection.commit()


def add_auto_institution(connection, autokmdb_news_id, institution_name, institution_id, found_name, found_position, name, classification_score, classification_label):
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_institutions
                (autokmdb_news_id, institution_name, institution_id, found_name, found_position, name, classification_score, classification_label)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, institution_name, institution_id, found_name, found_position, name, classification_score, classification_label))
    connection.commit()


def add_auto_place(connection, autokmdb_news_id, place_name, place_id, found_name, found_position, name, classification_score, classification_label):
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_places
                (autokmdb_news_id, place_name, place_id, found_name, found_position, name, classification_score, classification_label)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, place_name, place_id, found_name, found_position, name, classification_score, classification_label))
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


def skip_download_error(connection, id):
    query = '''UPDATE autokmdb_news SET skip_reason = 3, processing_step = 5
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


def get_articles(connection, page, status, domain=-1):
    query = ''

    selection = '''SELECT n.id AS id, clean_url AS url, description, title, source, newspaper_name, newspaper_id, n.classification_score AS classification_score,
            n.text AS text, n.cre_time AS date,
            (SELECT GROUP_CONCAT(CONCAT('{"name":"', p.name, '", "id":',p.id, ', "db_id":',COALESCE(p.person_id, 'null'), ', "db_name": "',COALESCE(p.person_name, 'null'), '", "classification_score":',p.classification_score, ', "classification_label":',p.classification_label, ', "annotation_label":',COALESCE(p.annotation_label, 'null'), ', "found_name":"',COALESCE(p.found_name, 'null'), '", "found_position":',COALESCE(p.found_position, 'null'),'}') SEPARATOR ',') FROM autokmdb_persons p WHERE n.id = p.autokmdb_news_id) AS persons,
            (SELECT GROUP_CONCAT(CONCAT('{"name":"', i.name, '", "id":',i.id, ', "db_id":',COALESCE(i.institution_id, 'null'), ', "db_name": "',COALESCE(i.institution_name, 'null'), '", "classification_score":',i.classification_score, ', "classification_label":',i.classification_label, ', "annotation_label":',COALESCE(i.annotation_label, 'null'), ', "found_name":"',COALESCE(i.found_name, 'null'), '", "found_position":',COALESCE(i.found_position, 'null'),'}') SEPARATOR ',') FROM autokmdb_institutions i WHERE n.id = i.autokmdb_news_id) AS institutions,
            (SELECT GROUP_CONCAT(CONCAT('{"name":"', pl.name, '", "id":',pl.id, ', "db_id":',COALESCE(pl.place_id, 'null'), ', "db_name": "',COALESCE(pl.place_name, 'null'), '", "classification_score":',pl.classification_score, ', "classification_label":',pl.classification_label, ', "annotation_label":',COALESCE(pl.annotation_label, 'null'), ', "found_name":"',COALESCE(pl.found_name, 'null'), '", "found_position":',COALESCE(pl.found_position, 'null'),'}') SEPARATOR ',') FROM autokmdb_places pl WHERE n.id = pl.autokmdb_news_id) AS places,
            (SELECT GROUP_CONCAT(CONCAT('{"name":"', o.name, '", "id":',o.id, ', "db_id":',COALESCE(o.other_id, 'null'), ', "classification_score":',o.classification_score, ', "classification_label":',o.classification_label, ', "annotation_label":',COALESCE(o.annotation_label, 'null'), '}') SEPARATOR ',') FROM autokmdb_others o WHERE n.id = o.autokmdb_news_id) AS others
        FROM autokmdb_news n
        '''
    group = ' GROUP BY id'

    if status == 'mixed':
        query = '''WHERE n.classification_label = 1 AND processing_step = 4 AND n.annotation_label IS NULL'''
    elif status == 'positive':
        query = '''WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 1'''
    elif status == 'negative':
        query = '''WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 0'''
    elif status == 'processing':
        query = '''WHERE processing_step < 4'''
    else:
        print('Invalid status provided!')
        return
    if domain and domain != -1 and isinstance(domain, int):
        query += ' AND n.newspaper_id = '+str(domain)

    with connection.cursor(dictionary=True) as cursor:
        cursor.execute('SET SESSION group_concat_max_len = 30000;')
        cursor.execute('SELECT COUNT(id) FROM autokmdb_news n '+query)
        count = cursor.fetchone()['COUNT(id)']
        cursor.execute(paginate_query(selection + query + group, 10, page))
        return count, cursor.fetchall()


def annote_negative(connection, id):
    query = '''UPDATE autokmdb_news SET annotation_label = 0, processing_step = 5 WHERE id = %s;'''
    with connection.cursor() as cursor:
        cursor.execute(query, (id,))
    connection.commit()


def annote_positive(connection, id, source_url, source_url_string, title, description, text, persons):
    query_1 = '''UPDATE autokmdb_news SET annotation_label = 1, processing_step = 5 WHERE id = %s;'''
    query_2 = '''INSERT INTO news_news (source_url, source_url_string) VALUES (%s, %s);'''
    query_3 = '''INSERT INTO news_lang (news_id, lang, name, teaser, articletext) VALUES (%s, %s, %s, %s, %s)'''

    query_p = '''INSERT INTO news_persons_link (news_id, person_id) VALUES (%s, %s)'''
    query_auto_p = '''UPDATE autokmdb_persons SET annotation_label = 1 WHERE id = %s;'''
    with connection.cursor() as cursor:
        cursor.execute(query_1, (id,))
        cursor.execute(query_2, (source_url, source_url_string))
        news_id = cursor.lastrowid
        print(news_id)
        cursor.execute(query_3, (news_id, 'hu', title, description, text))
        for person in persons:
            cursor.execute(query_p, (news_id, person['db_id']))
            cursor.execute(query_auto_p, (person['id'],))
        # TODO add other entities
    connection.commit()


def save_ner_step(connection, id):
    query = '''UPDATE autokmdb_news SET processing_step = 3 WHERE id = %s;'''
    with connection.cursor() as cursor:
        cursor.execute(query, (id,))
    connection.commit()


def save_keyword_step(connection, id):
    query = '''UPDATE autokmdb_news SET processing_step = 4 WHERE id = %s;'''
    with connection.cursor() as cursor:
        cursor.execute(query, (id,))
    connection.commit()


def get_rss_urls(connection):
    query = '''SELECT newspaper_id as id, name, rss_url FROM news_newspapers WHERE status = "Y";'''
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return cursor.fetchall()
