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


def get_all(table, id_column, name_column, limit=3):
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
    with mysql_db.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return list(cursor.fetchall())


def get_all_persons():
    return get_all('news_persons', 'person_id', 'name')


def get_all_institutions():
    return get_all('news_institutions', 'institution_id', 'name')


def get_all_places():
    return get_all('news_places', 'place_id', 'name_hu')


def get_all_others():
    return get_all('news_others', 'other_id', 'name')


def get_all_newspapers():
    return get_all('news_newspapers', 'newspaper_id', 'name')


def init_news(source, added_by, source_url, clean_url, processing_step):
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
    with mysql_db.cursor(dictionary=True) as cursor:
        query = """INSERT INTO autokmdb_news
                (source, added_by, source_url, clean_url, processing_step)
                VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(query, (source, added_by, source_url, clean_url,
                               processing_step))
        mysql_db.commit()


def add_auto_person(autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label):
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
    with mysql_db.cursor() as cursor:
        query = """INSERT INTO autokmdb_persons 
                (autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label))
        mysql_db.commit()


def add_auto_institution(autokmdb_news_id, institution_id, found_name, found_position, name, classification_score, classification_label):
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
    with mysql_db.cursor() as cursor:
        query = """INSERT INTO autokmdb_institutions 
                (autokmdb_news_id, institution_id, found_name, found_position, name, classification_score, classification_label) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, institution_id, found_name, found_position, name, classification_score, classification_label))
        mysql_db.commit()


def add_auto_place(autokmdb_news_id, place_id, found_name, found_position, name, classification_score, classification_label):
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
    with mysql_db.cursor() as cursor:
        query = """INSERT INTO autokmdb_places
                (autokmdb_news_id, place_id, found_name, found_position, name, classification_score, classification_label)
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, place_id, found_name, found_position, name, classification_score, classification_label))
        mysql_db.commit()


def add_auto_other(autokmdb_news_id, other_id, found_name, found_position, name, classification_score, classification_label):
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
    with mysql_db.cursor() as cursor:
        query = """INSERT INTO autokmdb_others
                (autokmdb_news_id, other_id, found_name, found_position, name, classification_score, classification_label)
                VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (autokmdb_news_id, other_id, found_name, found_position, name, classification_score, classification_label))
        mysql_db.commit()
