from functools import cache
import mysql.connector
import os
from contextlib import closing
from datetime import datetime
from slugify import slugify

connection_pool = mysql.connector.pooling.MySQLConnectionPool(
  pool_name="cnx_pool",
  pool_size=10,
  pool_reset_session=True,
  host=os.environ["MYSQL_HOST"],
  port=os.environ["MYSQL_PORT"],
  user=os.environ["MYSQL_USER"],
  password=os.environ["MYSQL_PASS"],
  database=os.environ["MYSQL_DB"],
)

VERSION_NUMBER = 0

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
    return get_all(connection, 'news_others', 'other_id', 'name_hu')


def get_all_files(connection):
    return get_all(connection, 'news_files', 'file_id', 'name_hu')


@cache
def get_all_newspapers(connection):
    query = '''SELECT n.newspaper_id AS id, n.name AS name, n.rss_url AS rss_url, COUNT(a.newspaper_id) AS article_count FROM news_newspapers n
    LEFT JOIN autokmdb_news a ON n.newspaper_id = a.newspaper_id WHERE n.status = "Y"
    GROUP BY n.newspaper_id, n.name, n.rss_url;'''
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        l = [{'id': r['id'],
                 'name': r['name'],
                 'has_rss': bool(r['rss_url']),
                 'article_count': r['article_count'],
                 } for r in cursor.fetchall()]
        l.sort(key=lambda r: r['article_count'], reverse=True)
        return l


def init_news(connection, source, source_url, clean_url, newspaper_name, newspaper_id):
    current_datetime = datetime.now()
    cre_time = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    with connection.cursor(dictionary=True) as cursor:
        query = """INSERT INTO autokmdb_news
                (source, source_url, clean_url, processing_step, cre_time, newspaper_name, newspaper_id, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (0 if source == 'rss' else 1, source_url, clean_url, 0, cre_time, newspaper_name, newspaper_id, VERSION_NUMBER))
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
                (autokmdb_news_id, person_name, person_id, found_name, found_position, name, classification_score, classification_label, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, person_name, person_id, found_name, found_position, name, classification_score, classification_label, VERSION_NUMBER))
    connection.commit()


def add_auto_institution(connection, autokmdb_news_id, institution_name, institution_id, found_name, found_position, name, classification_score, classification_label):
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_institutions
                (autokmdb_news_id, institution_name, institution_id, found_name, found_position, name, classification_score, classification_label, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, institution_name, institution_id, found_name, found_position, name, classification_score, classification_label, VERSION_NUMBER))
    connection.commit()


def add_auto_place(connection, autokmdb_news_id, place_name, place_id, found_name, found_position, name, classification_score, classification_label):
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_places
                (autokmdb_news_id, place_name, place_id, found_name, found_position, name, classification_score, classification_label, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, place_name, place_id, found_name, found_position, name, classification_score, classification_label, VERSION_NUMBER))
    connection.commit()


def add_auto_other(connection, autokmdb_news_id, other_id, found_name, found_position, name, classification_score, classification_label):
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_others
                (autokmdb_news_id, other_id, found_name, found_position, name, classification_score, classification_label, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, other_id, found_name, found_position, name, classification_score, classification_label, VERSION_NUMBER))
    connection.commit()


def save_download_step(connection, id, text, title, description, authors, date, is_paywalled):
    query = '''UPDATE autokmdb_news SET text = %s, title = %s, description = %s, processing_step = 1, author = %s, article_date = %s, is_paywalled = %s
               WHERE id = %s;'''
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (text, title, description, authors, date, is_paywalled, id))
    connection.commit()


def skip_same_news(connection, id, text, title, description, authors, date, is_paywalled):
    query = '''UPDATE autokmdb_news SET skip_reason = 2, processing_step = 5, text = %s, title = %s, description = %s, processing_step = 1, author = %s, article_date = %s, is_paywalled = %s
               WHERE id = %s'''
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (text, title, description, authors, date, is_paywalled, id))
    connection.commit()


def skip_download_error(connection, id):
    query = '''UPDATE autokmdb_news SET skip_reason = 3, processing_step = 5
               WHERE id = %s'''
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (id,))
    connection.commit()


def save_classification_step(connection, id, classification_label, classification_score, category):
    query = '''UPDATE autokmdb_news SET classification_label = %s,
               classification_score = %s, processing_step = 2, category = %s WHERE id = %s'''
    with connection.cursor() as cursor:
        cursor.execute(query, (classification_label, classification_score, category, id))
    connection.commit()


def get_step_queue(connection, step):
    fields = {
        0: 'clean_url AS url, source',
        1: 'title, description, text, source',
        2: 'text',
        3: 'text',
        4: 'text',
    }
    query = f'''SELECT id, {fields[step]} FROM autokmdb_news
               WHERE processing_step = {step} ORDER BY source DESC, mod_time DESC LIMIT 1'''
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


def get_article_counts(connection, domain=-1, q=''):
    article_counts = {}
    for status in ['mixed', 'positive', 'negative', 'processing', 'all']:
        if status == 'mixed':
            query = '''WHERE n.classification_label = 1 AND processing_step = 4 AND n.annotation_label IS NULL AND (n.skip_reason = 0 OR n.skip_reason is NULL)'''
        elif status == 'positive':
            query = '''WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 1'''
        elif status == 'negative':
            query = '''WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 0'''
        elif status == 'processing':
            query = '''WHERE processing_step < 4'''
        elif status == 'all':
            query = '''WHERE processing_step >= 0'''
        if domain and domain != -1 and isinstance(domain, int):
            query += ' AND n.newspaper_id = '+str(domain)
        query += ' AND (n.title LIKE %s OR n.description LIKE %s OR n.source_url LIKE %s OR n.newspaper_id LIKE %s)'
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT COUNT(id) FROM autokmdb_news n '+query, (q,q,q,q))
            count = cursor.fetchone()['COUNT(id)']
            article_counts[status] = count
    return article_counts


def get_article_institutions(cursor, id):
    query = '''SELECT name, id, institution_id AS db_id, institution_name AS db_name, classification_score, classification_label, annotation_label, found_name, found_position FROM autokmdb_institutions WHERE autokmdb_news_id = %s'''
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article_persons(cursor, id):
    query = '''SELECT name, id, person_id AS db_id, person_name AS db_name, classification_score, classification_label, annotation_label, found_name, found_position FROM autokmdb_persons WHERE autokmdb_news_id = %s'''
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article_places(cursor, id):
    query = '''SELECT name, id, place_id AS db_id, place_name AS db_name, classification_score, classification_label, annotation_label, found_name, found_position FROM autokmdb_places WHERE autokmdb_news_id = %s'''
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article_others(cursor, id):
    query = '''SELECT name, id, other_id AS db_id, classification_score, classification_label, annotation_label FROM autokmdb_others WHERE autokmdb_news_id = %s'''
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article(connection, id):
    query = '''SELECT n.id AS id, clean_url AS url, description, title, source, newspaper_name, newspaper_id, n.classification_score AS classification_score, annotation_label, processing_step, skip_reason,
            n.text AS text, n.cre_time AS date, category, article_date FROM autokmdb_news n WHERE id = %s
        '''
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute('SET SESSION group_concat_max_len = 30000;')
        cursor.execute(query, (id,))
        article = cursor.fetchone()
        article['persons'] = get_article_persons(cursor, id)
        article['institutions'] = get_article_institutions(cursor, id)
        article['places'] = get_article_places(cursor, id)
        article['others'] = get_article_others(cursor, id)
        return article


def get_articles(connection, page, status, domain=-1, q=''):
    query = ''

    selection = '''SELECT n.id AS id, clean_url AS url, description, title, source, newspaper_name, newspaper_id, n.classification_score AS classification_score, annotation_label, processing_step, skip_reason, negative_reason,
            n.cre_time AS date, category
        FROM autokmdb_news n
        '''
    group = ' GROUP BY id ORDER BY source DESC, n.mod_time DESC'

    if status == 'mixed':
        query = '''WHERE n.classification_label = 1 AND processing_step = 4 AND n.annotation_label IS NULL AND (n.skip_reason = 0 OR n.skip_reason is NULL)'''
    elif status == 'positive':
        query = '''WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 1'''
    elif status == 'negative':
        query = '''WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 0'''
    elif status == 'processing':
        query = '''WHERE processing_step < 4'''
    elif status == 'all':
        query = '''WHERE processing_step >= 0'''
    else:
        print('Invalid status provided!')
        return
    if domain and domain != -1 and isinstance(domain, int):
        query += ' AND n.newspaper_id = '+str(domain)

    query += ' AND (n.title LIKE %s OR n.description LIKE %s OR n.source_url LIKE %s OR n.newspaper_id LIKE %s)'

    with connection.cursor(dictionary=True) as cursor:
        cursor.execute('SELECT COUNT(id) FROM autokmdb_news n '+query, (q,q,q,q))
        count = cursor.fetchone()['COUNT(id)']
        cursor.execute(paginate_query(selection + query + group, 10, page), (q,q,q,q))
        return count, cursor.fetchall()


def annote_negative(connection, id, reason):
    query = '''UPDATE autokmdb_news SET annotation_label = 0, processing_step = 5, negative_reason = %s WHERE id = %s;'''
    query_id = '''SELECT news_id FROM autokmdb_news WHERE id = %s;'''
    query_remove = '''DELETE FROM news_news WHERE news_id = %s;'''
    query_remove_person = '''DELETE FROM news_persons_link WHERE news_id = %s;'''
    query_remove_institution = '''DELETE FROM news_institutions_link WHERE news_id = %s;'''
    query_remove_place = '''DELETE FROM news_places_link WHERE news_id = %s;'''
    query_remove_other = '''DELETE FROM news_others_link WHERE news_id = %s;'''
    query_remove_lang = '''DELETE FROM news_lang WHERE news_id = %s;'''

    with connection.cursor() as cursor:
        cursor.execute(query_id, (id,))
        news_id = cursor.fetchone()[0]
        cursor.execute(query, (reason, id,))
        if news_id:
            cursor.execute(query_remove, (news_id,))
            cursor.execute(query_remove_person, (news_id,))
            cursor.execute(query_remove_institution, (news_id,))
            cursor.execute(query_remove_place, (news_id,))
            cursor.execute(query_remove_other, (news_id,))
            cursor.execute(query_remove_lang, (news_id,))
    connection.commit()


def create_person(connection, name, user_id):
    print('adding', name)
    query = '''INSERT INTO news_persons (status, name, cre_id, mod_id, import_id, cre_time, mod_time) VALUES (%s, %s, %s, %s, %s, %s, %s);'''
    query_seo = '''INSERT INTO tags_seo_data (seo_name, tag_type, item_id) VALUES (%s, %s, %s);'''
    current_datetime = datetime.now()
    cre_time = int(current_datetime.timestamp())

    with connection.cursor() as cursor:
        cursor.execute(query, ('Y', name, user_id, user_id, 0, cre_time, cre_time))
        db_id = cursor.lastrowid
        cursor.execute(query_seo, (slugify(name), 'persons', db_id))
        print(db_id)
    connection.commit()
    return db_id


def create_institution(connection, name, user_id):
    query = '''INSERT INTO news_institutions (status, name, cre_id, mod_id, import_id, cre_time, mod_time) VALUES (%s, %s, %s, %s, %s, %s, %s);'''
    query_seo = '''INSERT INTO tags_seo_data (seo_name, tag_type, item_id) VALUES (%s, %s, %s);'''
    current_datetime = datetime.now()
    cre_time = int(current_datetime.timestamp())

    with connection.cursor() as cursor:
        cursor.execute(query, ('Y', name, user_id, user_id, 0, cre_time, cre_time))
        db_id = cursor.lastrowid
        cursor.execute(query_seo, (slugify(name), 'institutions', db_id))
    connection.commit()
    return db_id


def annote_positive(connection, id, source_url, source_url_string, title, description, text, persons, institutions, places, newspaper_id, user_id, is_active, category, others, file_id):
    query_1 = '''UPDATE autokmdb_news SET annotation_label = 1, processing_step = 5, news_id = %s WHERE id = %s;'''
    query_2 = '''INSERT INTO news_news (source_url, source_url_string, cre_time, mod_time, pub_time, cre_id, mod_id, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);'''
    query_3 = '''INSERT INTO news_lang (news_id, lang, name, teaser, articletext, alias, seo_url_default) VALUES (%s, %s, %s, %s, %s, %s, %s)'''
    query_np = '''INSERT INTO news_newspapers_link (news_id, newspaper_id) VALUES (%s, %s);'''
    query_cat = '''INSERT INTO news_categories_link (news_id, cid, head) VALUES (%s, %s, %s);'''

    query_p = '''INSERT INTO news_persons_link (news_id, person_id) VALUES (%s, %s)'''
    query_auto_p = '''UPDATE autokmdb_persons SET annotation_label = 1 WHERE id = %s;'''
    query_i = '''INSERT INTO news_institutions_link (news_id, institution_id) VALUES (%s, %s)'''
    query_auto_i = '''UPDATE autokmdb_institutions SET annotation_label = 1 WHERE id = %s;'''
    query_pl = '''INSERT INTO news_places_link (news_id, place_id) VALUES (%s, %s)'''
    query_auto_pl = '''UPDATE autokmdb_places SET annotation_label = 1 WHERE id = %s;'''
    query_others = '''INSERT INTO news_others_link (news_id, other_id) VALUES (%s, %s)'''
    query_file = '''INSERT INTO news_files_link (news_id, file_id) VALUES (%s, %s)'''

    current_datetime = datetime.now()
    cre_time = int(current_datetime.timestamp())

    with connection.cursor() as cursor:
        alias = slugify(title)
        seo_url_default = 'hirek/magyar-hirek/'+alias
        cursor.execute(query_2, (source_url, source_url_string, cre_time, cre_time, cre_time, user_id, user_id, 'Y' if is_active else 'N'))
        news_id = cursor.lastrowid
        cursor.execute(query_1, (news_id, id))
        cursor.execute(query_3, (news_id, 'hu', title, description, text.replace('\n', '<br>'), alias, seo_url_default))
        for person in persons:
            if ('db_id' not in person or not person['db_id']) and person['name']:
                db_id = create_person(connection, person['name'], user_id)
                person['db_id'] = db_id
        for institution in institutions:
            if ('db_id' not in institution or not institution['db_id']) and institution['name']:
                db_id = create_institution(connection, institution['name'], user_id)
                institution['db_id'] = db_id

        cursor.execute(query_np, (news_id, newspaper_id))
        category_dict = {0: 5, 1: 6, 2:7, None: 5}
        cursor.execute(query_cat, (news_id, category_dict[category], "Y"))

        done_person_ids = set()
        done_institution_ids = set()
        done_place_ids = set()
        for person in persons:
            if person['db_id'] not in done_person_ids:
                cursor.execute(query_p, (news_id, person['db_id']))
                done_person_ids.add(person['db_id'])
            if 'id' in person and isinstance(person['id'], int):
                cursor.execute(query_auto_p, (person['id'],))
        for institution in institutions:
            if institution['db_id'] not in done_institution_ids:
                cursor.execute(query_i, (news_id, institution['db_id']))
                done_institution_ids.add(institution['db_id'])
            if 'id' in institution and isinstance(institution['id'], int):
                cursor.execute(query_auto_i, (institution['id'],))
        for place in places:
            if place['db_id'] not in done_place_ids:
                cursor.execute(query_pl, (news_id, place['db_id']))
                done_place_ids.add(place['db_id'])
            if 'id' in place and isinstance(place['id'], int):
                cursor.execute(query_auto_pl, (place['id'],))
        for other in others:
            cursor.execute(query_others, (news_id, other['db_id']))
        if file_id > 0:
            cursor.execute(query_file, (news_id, file_id))
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


def validate_session(connection, session_id):
    if 'NO_LOGIN' in os.environ:
        return True
    query = '''SELECT * FROM users_sessions WHERE session_id = %s;'''
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (session_id,))
        session = cursor.fetchone()
    if session is None or session['registered'] == 0:
        return None
    return session['registered']


def get_roles(connection, session_id):
    query = '''SELECT * FROM users_sessions WHERE session_id = %s;'''
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (session_id,))
    session = cursor.fetchone()
    if session is None or session['registered'] == 0:
        return []

    user_id = session['registered']

    query_u = '''SELECT * FROM users_modul_rights WHERE user_id = %s;'''

    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query_u, (user_id,))

    roles = [{'modul_name': r['modul_name'], 'action_name': r['action_name'], 'action_right': r['action_right']} for r in cursor.fetchall()]

    return roles