from functools import cache
import mysql.connector
import os
from contextlib import closing


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
    """
    This function retrieves a limited number of records from a specified MySQL table where the status is 'Y'.

    Args:
        table (str): The name of the table from which to retrieve records.
        id_column (str): The name of the column to be used as the ID in the retrieved records.
        name_column (str): The name of the column to be used as the name in the retrieved records.
        limit (int, optional): The maximum number of records to retrieve. Defaults to 3.

    Returns:
        list: A list of dictionaries, where each dictionary represents a record from the table and contains the ID and name.
    """
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
    """
    This function is used to insert news data into the 'autokmdb_news' table in the MySQL database.

    Parameters:
    source (str): The source from where the news is obtained.
    added_by (str): The person who added the news.
    source_url (str): The original URL of the news.
    clean_url (str): The sanitized URL of the news.
    processing_step (str): The current step in the processing pipeline.

    Returns:
    None
    """

    with connection.cursor(dictionary=True) as cursor:
        query = """INSERT INTO autokmdb_news
                (source, source_url, clean_url, processing_step)
                VALUES (%s, %s, %s, %s)"""
        cursor.execute(query, (0 if source == 'rss' else 1, source_url, clean_url, 0))
    connection.commit()


def check_url_exists(connection, url):
    with connection.cursor() as cursor:
        query = "SELECT id FROM autokmdb_news WHERE clean_url = %s"
        cursor.execute(query, (url,))
        results = cursor.fetchall()

        return len(results) != 0


def add_auto_person(connection, autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label):
    """
    This function adds a person to the 'autokmdb_persons' table in the MySQL database.

    Parameters:
    autokmdb_news_id (int): The ID of the news article from the autokmdb_news where the person was found.
    person_id (int): The unique ID of the person.
    found_name (str): The name of the person as found in the news article.
    found_position (str): The position of the person as found in the news article.
    name (str): The actual name of the person.
    classification_score (float): The score given by the classification model for the person.
    classification_label (str): The label given by the classification model for the person.

    Returns:
    None
    """
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_persons 
                (autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label))
    connection.commit()


def add_auto_institution(connection, autokmdb_news_id, institution_id, found_name, found_position, name, classification_score, classification_label):
    """
    This function adds an institution to the 'autokmdb_institutions' table in the MySQL database.

    Parameters:
    autokmdb_news_id (int): The ID of the news article from the autokmdb_news where the institution was found.
    institution_id (int): The unique ID of the institution.
    found_name (str): The name of the institution as found in the news article.
    found_position (str): The position of the institution as found in the news article.
    name (str): The actual name of the institution.
    classification_score (float): The score given by the classification model for the institution.
    classification_label (str): The label given by the classification model for the institution.

    Returns:
    None
    """
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_institutions 
                (autokmdb_news_id, institution_id, found_name, found_position, name, classification_score, classification_label) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, institution_id, found_name, found_position, name, classification_score, classification_label))
    connection.commit()


def add_auto_place(connection, autokmdb_news_id, place_id, found_name, found_position, name, classification_score, classification_label):
    """
    This function adds a place to the 'autokmdb_places' table in the MySQL database.

    Parameters:
    autokmdb_news_id (int): The ID of the news article from the autokmdb_news where the place was found.
    place_id (int): The unique ID of the place.
    found_name (str): The name of the place as found in the news article.
    found_position (str): The position of the place as found in the news article.
    name (str): The actual name of the place.
    classification_score (float): The score given by the classification model for the place.
    classification_label (str): The label given by the classification model for the place.

    Returns:
    None
    """
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_places
                (autokmdb_news_id, place_id, found_name, found_position, name, classification_score, classification_label)
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, place_id, found_name, found_position, name, classification_score, classification_label))
    connection.commit()


def add_auto_other(connection, autokmdb_news_id, other_id, found_name, found_position, name, classification_score, classification_label):
    """
    This function adds an 'other' to the 'autokmdb_others' table in the MySQL database.

    Parameters:
    autokmdb_news_id (int): The ID of the news article from the autokmdb_news where the 'other' was found.
    other_id (int): The unique ID of the 'other'.
    found_name (str): The name of the 'other' as found in the news article.
    found_position (str): The position of the 'other' as found in the news article.
    name (str): The actual name of the 'other'.
    classification_score (float): The score given by the classification model for the 'other'.
    classification_label (str): The label given by the classification model for the 'other'.

    Returns:
    None
    """
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
    """
    This function fetches the data from the 'autokmdb_news' table 
    in the database where the processing_step is the given step. It returns the result as a list of dictionaries.

    Args:
    step (int): The processing step to fetch data for.

    Returns:
    list: A list of dictionaries where each dictionary represents a row from the query result.
    Each dictionary contains 'id' and the relevant data as keys.

    Example:
    [{'id': 1, 'url': 'http://example.com'}, {'id': 2, 'url': 'http://example2.com'}, ...]
    """
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

    selection = 'SELECT id, clean_url, description, title, source, classification_score, text FROM autokmdb_news '

    if status == 'mixed':
        query = '''WHERE classification_label = 1 AND processing_step = 3 AND annotation_label IS NULL AND clean_url LIKE %s'''
    elif status == 'positive':
        query = '''WHERE classification_label = 1 AND processing_step = 5 AND annotation_label = 1 AND clean_url LIKE %s'''
    elif status == 'negative':
        query = '''WHERE classification_label = 1 AND processing_step = 5 AND annotation_label = 0 AND clean_url LIKE %s'''
    else:
        print('Invalid status provided!')
        return

    with connection.cursor(dictionary=True) as cursor:
        cursor.execute('SELECT COUNT(*) FROM autokmdb_news '+query, (domain,))
        count = cursor.fetchone()
        cursor.execute(paginate_query(selection + query, 10, page), (domain,))
        return count['COUNT(*)'], cursor.fetchall()


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
