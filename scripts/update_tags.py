import sys
import csv
import mysql.connector
import os
from dotenv import load_dotenv
from mysql.connector.pooling import MySQLConnectionPool, PooledMySQLConnection
from functools import cache

load_dotenv('../../.env.prod')

connection_pool = mysql.connector.pooling.MySQLConnectionPool(
  pool_name="cnx_pool",
  pool_size=1,
  pool_reset_session=True,
  host=os.environ["MYSQL_HOST"],
  port=os.environ["MYSQL_PORT"],
  user=os.environ["MYSQL_USER"],
  password=os.environ["MYSQL_PASS"],
  database=os.environ["MYSQL_DB"],
)


@cache
def get_all(
    connection: PooledMySQLConnection, table: str, id_column: str, name_column: str
):
    """
    Queries label id-name pairs from given table.

    Args:
        connection: db connection
        table: name of the table
        id_column: name of the column containing the ids
        name_column: name of the column containing the names

    Returns:
        List of dirs, each dir containing the 'name' and 'id' of a given label.
    """
    query = f'SELECT {id_column} AS id, {name_column} AS name FROM {table} WHERE status = "Y";'
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return list(cursor.fetchall())


def get_all_persons(connection: PooledMySQLConnection):
    """
    Queries person label id-name pairs.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' of a person and 'id' of its label.
    """
    return get_all(connection, "news_persons", "person_id", "name")


def get_all_institutions(connection: PooledMySQLConnection):
    """
    Queries institution label id-name pairs.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' of an institution and 'id' of its label.
    """
    return get_all(connection, "news_institutions", "institution_id", "name")


def get_all_places(connection: PooledMySQLConnection):
    """
    Queries place label id-name pairs.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' of a place and 'id' of its label.
    """
    return get_all(connection, "news_places", "place_id", "name_hu")


def get_all_others(connection: PooledMySQLConnection):
    """
    Queries other label id-name pairs.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' of the label and its 'id'.
    """
    return get_all(connection, "news_others", "other_id", "name_hu")


def get_all_files(connection: PooledMySQLConnection):
    """
    Queries file id-name pairs.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' of the file and its 'id'.
    """
    return get_all(connection, "news_files", "file_id", "name_hu")



with connection_pool.get_connection() as connection:
    all_persons = get_all_persons(connection)
    all_institutions = get_all_institutions(connection)
    all_places = get_all_places(connection)
    all_others = get_all_others(connection)
    all_persons_by_id = {person["id"]: person["name"] for person in all_persons}
    all_institutions_by_id = {
        institution["id"]: institution["name"] for institution in all_institutions
    }
    all_places_by_id = {place["id"]: place["name"] for place in all_places}
    all_others_by_id = {other["id"]: other["name"] for other in all_others}



def setTags(cursor, news_id, persons, newspaper, institutions, places, others):
    names: list[str] = [person['name'] for person in persons]
    names += [institution['name'] for institution in institutions]
    names.append(newspaper)
    names += [institution['name'] for institution in institutions]
    names += [place['name'] for place in places]
    names += [other['name'] for other in others]

    names_str: str = '|'.join(names)

    tag_query = """SELECT tag_id FROM news_tags WHERE news_id = %s"""
    tag_update = """UPDATE news_tags SET names = %s WHERE tag_id = %s"""
    tag_insert = """INSERT INTO news_tags (names, news_id) VALUES (%s, %s)"""

    cursor.execute(tag_query, (news_id,))
    tag_id = cursor.fetchone()

    if tag_id and tag_id[0]:
        cursor.execute(tag_update, (names_str, news_id,))
    else:
        cursor.execute(tag_insert, (names_str, news_id,))



def get_article_persons_kmdb(cursor, id):
    query = (
        """SELECT news_id, person_id AS id FROM news_persons_link WHERE news_id = %s"""
    )
    cursor.execute(query, (id,))
    return [
        {
            "annotation_label": 1,
            "db_id": row["id"],
            "name": all_persons_by_id[row["id"]],
            "db_name": all_persons_by_id[row["id"]],
        }
        for row in cursor.fetchall()
        if row["id"] in all_persons_by_id
    ]


def get_article_institutions_kmdb(cursor, id):
    query = """SELECT news_id, institution_id AS id FROM news_institutions_link WHERE news_id = %s"""
    cursor.execute(query, (id,))
    return [
        {
            "annotation_label": 1,
            "db_id": row["id"],
            "name": all_institutions_by_id[row["id"]],
            "db_name": all_institutions_by_id[row["id"]],
        }
        for row in cursor.fetchall()
        if row["id"] in all_institutions_by_id
    ]


def get_article_places_kmdb(cursor, id):
    query = (
        """SELECT news_id, place_id AS id FROM news_places_link WHERE news_id = %s"""
    )
    cursor.execute(query, (id,))
    return [
        {
            "annotation_label": 1,
            "db_id": row["id"],
            "name": all_places_by_id[row["id"]],
            "db_name": all_places_by_id[row["id"]],
        }
        for row in cursor.fetchall()
        if row["id"] in all_places_by_id
    ]


def get_article_others_kmdb(cursor, id):
    query = (
        """SELECT news_id, other_id AS id FROM news_others_link WHERE news_id = %s"""
    )
    cursor.execute(query, (id,))
    return [
        {
            "annotation_label": 1,
            "db_id": row["id"],
            "name": all_others_by_id[row["id"]],
            "db_name": all_others_by_id[row["id"]],
        }
        for row in cursor.fetchall()
        if row["id"] in all_others_by_id
    ]


def get_article_persons(cursor, id):
    query = """SELECT name, id, person_id AS db_id, person_name AS db_name, classification_score, classification_label, annotation_label, found_name, found_position FROM autokmdb_persons WHERE autokmdb_news_id = %s"""
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article_institutions(cursor, id):
    query = """SELECT name, id, institution_id AS db_id, institution_name AS db_name, classification_score, classification_label, annotation_label, found_name, found_position FROM autokmdb_institutions WHERE autokmdb_news_id = %s"""
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article_places(cursor, id):
    query = """SELECT name, id, place_id AS db_id, place_name AS db_name, classification_score, classification_label, annotation_label, found_name, found_position FROM autokmdb_places WHERE autokmdb_news_id = %s"""
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article_others(cursor, id):
    query = """SELECT name, id, other_id AS db_id, classification_score, classification_label, annotation_label FROM autokmdb_others WHERE autokmdb_news_id = %s"""
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article(cursor, id):
    query = """SELECT n.id AS id, news_id, clean_url AS url, description, title, source, newspaper_name, newspaper_id, n.classification_score AS classification_score, n.classification_label AS classification_label, annotation_label, processing_step, skip_reason,
            n.text AS text, n.cre_time AS date, category, CONVERT_TZ(article_date, @@session.time_zone, '+00:00') as article_date, u.name AS mod_name FROM autokmdb_news n LEFT JOIN users u ON n.mod_id = u.user_id WHERE id = %s
        """
    cursor.execute(query, (id,))
    article = cursor.fetchone()
    if article["news_id"]:
        article["persons"] = get_article_persons_kmdb(
            cursor, article["news_id"]
        ) + get_article_persons(cursor, id)
        article["institutions"] = get_article_institutions_kmdb(
            cursor, article["news_id"]
        ) + get_article_institutions(cursor, id)
        article["places"] = get_article_places_kmdb(
            cursor, article["news_id"]
        ) + get_article_places(cursor, id)
        article["others"] = get_article_others_kmdb(
            cursor, article["news_id"]
        ) + get_article_others(cursor, id)
    else:
        article["persons"] = get_article_persons(cursor, id)
        article["institutions"] = get_article_institutions(cursor, id)
        article["places"] = get_article_places(cursor, id)
        article["others"] = get_article_others(cursor, id)
    return article


def setTags(cursor, news_id, persons, newspaper, institutions, places, others):
    names: list[str] = [person['db_name'] for person in persons]
    names.append(newspaper)
    names += [institution['db_name'] for institution in institutions]
    names += [place['db_name'] for place in places]
    names += [other['db_name'] for other in others]

    names_str: str = '|'.join(names)

    tag_query = """SELECT tag_id FROM news_tags WHERE news_id = %s"""
    tag_update = """UPDATE news_tags SET names = %s WHERE tag_id = %s"""
    tag_insert = """INSERT INTO news_tags (names, news_id) VALUES (%s, %s)"""

    cursor.execute(tag_query, (news_id,))
    tag_id = cursor.fetchone()

    if tag_id and tag_id[0]:
        cursor.execute(tag_update, (names_str, news_id,))
    else:
        cursor.execute(tag_insert, (names_str, news_id,))


def deduplicate_dicts(data, key):
    seen = set()
    deduplicated = []
    
    for item in data:
        value = item[key]
        if value not in seen and item['annotation_label'] == 1:
            seen.add(value)
            deduplicated.append(item)
    
    return deduplicated


with connection_pool.get_connection() as connection:
    with connection.cursor(dictionary=True) as cursor:
        print('running query')
        cursor.execute('''SELECT nn.id
FROM autokmdb_news nn
LEFT JOIN news_tags nt ON nn.news_id = nt.news_id
WHERE nt.news_id IS NULL AND nn.news_id;''')
        rows = cursor.fetchall()
        print(len(rows))
        print(rows[:100])
        for row in rows:
            article = get_article(cursor, row['id'])
            print(article['news_id'])
            print(deduplicate_dicts([a for a in article['persons'] if a['db_id']], 'db_id'))
            setTags(cursor, article['news_id'], deduplicate_dicts([a for a in article['persons'] if a['db_id']], 'db_id'), article['newspaper_name'], deduplicate_dicts([a for a in article['institutions'] if a['db_id']], 'db_id'), deduplicate_dicts([a for a in article['places'] if a['db_id']], 'db_id'), deduplicate_dicts([a for a in article['others'] if a['db_id']], 'db_id'))
            connection.commit()