from functools import cache
from typing import Literal, Any, Optional
from mysql.connector.pooling import MySQLConnectionPool, PooledMySQLConnection
import os
from slugify import slugify
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from cachetools import cached, LRUCache, TTLCache

connection_pool: MySQLConnectionPool = MySQLConnectionPool(
    pool_name="cnx_pool",
    pool_size=20,
    pool_reset_session=True,
    host=os.environ["MYSQL_HOST"],
    port=os.environ["MYSQL_PORT"],
    user=os.environ["MYSQL_USER"],
    password=os.environ["MYSQL_PASS"],
    database=os.environ["MYSQL_DB"],
    use_pure=True,
)

VERSION_NUMBER: int = 0


@cached(cache=TTLCache(maxsize=32, ttl=60))
def get_all(table: str, id_column: str, name_column: str) -> list[dict]:
    """
    Queries label id-name pairs from given table.

    Args:
        table: name of the table
        id_column: name of the column containing the ids
        name_column: name of the column containing the names

    Returns:
        List of dicts, each dict containing the 'name' and 'id' of a given label.
    """
    query = f'SELECT {id_column} AS id, {name_column} AS name FROM {table} WHERE status = "Y";'
    with connection_pool.get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return list(cursor.fetchall())


def get_all_persons() -> list[dict]:
    """
    Queries person label id-name pairs.

    Returns:
        List of dicts, each dict containing the 'name' of a person and 'id' of its label.
    """
    return get_all("news_persons", "person_id", "name")


def get_all_institutions() -> list[dict]:
    """
    Queries institution label id-name pairs.

    Returns:
        List of dicts, each dict containing the 'name' of an institution and 'id' of its label.
    """
    return get_all("news_institutions", "institution_id", "name")


def get_all_places() -> list[dict]:
    """
    Queries place label id-name pairs.

    Returns:
        List of dicts, each dict containing the 'name' of a place and 'id' of its label.
    """
    return get_all("news_places", "place_id", "name_hu")


def get_all_others() -> list[dict]:
    """
    Queries other label id-name pairs.

    Returns:
        List of dicts, each dict containing the 'name' of the label and its 'id'.
    """
    return get_all("news_others", "other_id", "name_hu")


def get_all_files() -> list[dict]:
    """
    Queries file id-name pairs.

    Returns:
        List of dicts, each dict containing the 'name' of the file and its 'id'.
    """
    return get_all("news_files", "file_id", "name_hu")


@cached(cache=TTLCache(maxsize=32, ttl=3600))
def get_all_newspapers() -> list[dict[str, Any]]:
    query = """SELECT n.newspaper_id AS id, n.name AS name, n.rss_url AS rss_url, COUNT(a.newspaper_id) AS article_count FROM news_newspapers n
    LEFT JOIN autokmdb_news a ON n.newspaper_id = a.newspaper_id WHERE n.status = "Y"
    GROUP BY n.newspaper_id, n.name, n.rss_url;"""
    with connection_pool.get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            l = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "has_rss": bool(r["rss_url"]),
                    "article_count": r["article_count"],
                }
                for r in cursor.fetchall()
            ]
            l.sort(key=lambda r: r["article_count"], reverse=True)
            return l


with connection_pool.get_connection() as connection:
    all_newspapers = get_all_newspapers()
    all_persons = get_all_persons()
    all_institutions = get_all_institutions()
    all_places = get_all_places()
    all_others = get_all_others()
    all_persons_by_id = {person["id"]: person["name"] for person in all_persons}
    all_institutions_by_id = {
        institution["id"]: institution["name"] for institution in all_institutions
    }
    all_places_by_id = {place["id"]: place["name"] for place in all_places}
    all_others_by_id = {other["id"]: other["name"] for other in all_others}


@cached(cache=TTLCache(maxsize=256, ttl=3600))
def get_all_freq(table: str, id_column: str, name_column: str) -> list[dict]:
    """
    Queries label id-name pairs from given table and counts number of times the given label has
    been used on an article.

    Args:
        table: name of the table
        id_column: name of the column containing the ids
        name_column: name of the column containing the names

    Returns:
        List of dicts, each dict containing the 'name', 'id' and 'count' occurrances of a given label.
    """
    query = f'SELECT p.{id_column} AS id, p.{name_column} AS name, COUNT(npl.news_id) AS count FROM {table} p JOIN {table}_link npl ON p.{id_column} = npl.{id_column} WHERE status = "Y" GROUP BY p.{id_column};'
    with connection_pool.get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return list(cursor.fetchall())


def get_all_persons_freq() -> list[dict]:
    """
    Queries person label id-name pairs and counts the number of times the given person label has
    been used on an article.

    Returns:
        List of dicts, each dict containing the 'name' and 'id' of a person label, as well as the
        'count' occurrances of the given label.
    """
    return get_all_freq("news_persons", "person_id", "name")


def get_all_institutions_freq() -> list[dict]:
    """
    Queries institution label id-name pairs and counts the number of times the given institution
    label has been used on an article.

    Returns:
        List of dicts, each dict containing the 'name' and 'id' of an institution label, as well as the
        'count' occurrances of the given label.
    """
    return get_all_freq("news_institutions", "institution_id", "name")


def get_all_places_freq() -> list[dict]:
    """
    Queries place label id-name pairs and counts the number of times the given place label has been
    used on an article.

    Returns:
        List of dicts, each dict containing the 'name' and 'id' of a place label, as well as the
        'count' occurrances of the given label.
    """
    return get_all_freq("news_places", "place_id", "name_hu")


def get_all_others_freq() -> list[dict]:
    return get_all_freq("news_others", "other_id", "name_hu")


def get_places_alias(connection: PooledMySQLConnection):
    query = """
    SELECT
        np.name_hu AS place_name,
        ap.alias_name
    FROM
        news_places np
        JOIN autokmdb_alias_place ap ON np.place_id = ap.place_id;
    """
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return list(cursor.fetchall())


def process_and_accept_article(
    connection: PooledMySQLConnection,
    id: int,
    user_id: int,
) -> None:
    query = """UPDATE autokmdb_news SET processing_step = 2, skip_reason = NULL, mod_id = %s, source = 1, classification_label = 1 WHERE id = %s;"""
    with connection.cursor() as cursor:
        cursor.execute(query, (user_id, id))
    connection.commit()


def init_news(
    connection: PooledMySQLConnection,
    source: str,
    source_url: str,
    clean_url: str,
    newspaper_name: str,
    newspaper_id: int,
    user_id: Optional[int],
    pub_time: Optional[str],
) -> None:
    current_datetime: datetime = datetime.now()
    cre_time: str = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    with connection.cursor(dictionary=True) as cursor:
        query = """INSERT INTO autokmdb_news
                (source, source_url, clean_url, processing_step, cre_time, article_date, newspaper_name, newspaper_id, version_number, mod_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(
            query,
            (
                0 if source == "rss" else 1,
                source_url,
                clean_url,
                0,
                cre_time,
                pub_time,
                newspaper_name,
                newspaper_id,
                VERSION_NUMBER,
                user_id,
            ),
        )
    connection.commit()


def url_exists_in_kmdb(connection: PooledMySQLConnection, url: str) -> bool:
    with connection.cursor() as cursor:
        query = "SELECT news_id FROM news_news WHERE source_url LIKE %s"
        cursor.execute(query, ("%" + url + "%",))
        results: list[dict] = cursor.fetchall()

        return len(results) != 0


def check_url_exists(connection: PooledMySQLConnection, url: str) -> bool:
    with connection.cursor() as cursor:
        query = "SELECT id FROM autokmdb_news WHERE clean_url = %s"
        cursor.execute(query, (url,))
        results: list[dict] = cursor.fetchall()

        return len(results) != 0


def add_auto_person(
    connection: PooledMySQLConnection,
    autokmdb_news_id: int,
    person_name: str,
    person_id: int,
    found_name: str,
    found_position: int,
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_persons
                (autokmdb_news_id, person_name, person_id, found_name, found_position, name, classification_score, classification_label, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(
            query,
            (
                autokmdb_news_id,
                person_name,
                person_id,
                found_name,
                found_position,
                name,
                classification_score,
                classification_label,
                VERSION_NUMBER,
            ),
        )
    connection.commit()


def add_auto_institution(
    connection: PooledMySQLConnection,
    autokmdb_news_id: int,
    institution_name: str,
    institution_id: int,
    found_name: str,
    found_position: int,
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_institutions
                (autokmdb_news_id, institution_name, institution_id, found_name, found_position, name, classification_score, classification_label, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(
            query,
            (
                autokmdb_news_id,
                institution_name,
                institution_id,
                found_name,
                found_position,
                name,
                classification_score,
                classification_label,
                VERSION_NUMBER,
            ),
        )
    connection.commit()


def add_auto_place(
    connection: PooledMySQLConnection,
    autokmdb_news_id: int,
    place_name: str,
    place_id: int,
    found_name: str,
    found_position: int,
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_places
                (autokmdb_news_id, place_name, place_id, found_name, found_position, name, classification_score, classification_label, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(
            query,
            (
                autokmdb_news_id,
                place_name,
                place_id,
                found_name,
                found_position,
                name,
                classification_score,
                classification_label,
                VERSION_NUMBER,
            ),
        )
    connection.commit()


def add_auto_other(
    connection: PooledMySQLConnection,
    autokmdb_news_id: int,
    other_id: int,
    found_name: str,
    found_position: int,
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_others
                (autokmdb_news_id, other_id, found_name, found_position, name, classification_score, classification_label, version_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(
            query,
            (
                autokmdb_news_id,
                other_id,
                found_name,
                found_position,
                name,
                classification_score,
                classification_label,
                VERSION_NUMBER,
            ),
        )
    connection.commit()


def save_download_step(
    connection: PooledMySQLConnection,
    id: int,
    text: str,
    title: str,
    description: str,
    authors: str,
    date: Optional[str],
    is_paywalled: int,
) -> None:
    query = """UPDATE autokmdb_news 
            SET text = %s, 
                title = %s, 
                description = %s, 
                processing_step = 1, 
                skip_reason = NULL, 
                author = %s, 
                article_date = COALESCE(%s, article_date),
                is_paywalled = %s
            WHERE id = %s;"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            query, (text, title, description, authors, date, is_paywalled, id)
        )
    connection.commit()


def skip_same_news(
    connection: PooledMySQLConnection,
    id: int,
    text: str,
    title: str,
    description: str,
    authors: str,
    date: Optional[str],
    is_paywalled: int,
) -> None:
    query = """UPDATE autokmdb_news SET skip_reason = 2, processing_step = 5, text = %s, title = %s, description = %s, processing_step = 1, author = %s, article_date = COALESCE(%s, article_date), is_paywalled = %s
               WHERE id = %s"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            query, (text, title, description, authors, date, is_paywalled, id)
        )
    connection.commit()


def skip_download_error(connection: PooledMySQLConnection, id: int) -> None:
    query = """UPDATE autokmdb_news SET skip_reason = 3, processing_step = 5
               WHERE id = %s"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (id,))
    connection.commit()


def skip_processing_error(connection: PooledMySQLConnection, id: int) -> None:
    query = """UPDATE autokmdb_news SET skip_reason = 4, processing_step = 5
               WHERE id = %s"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (id,))
    connection.commit()


def save_classification_step(
    connection: PooledMySQLConnection,
    id: int,
    classification_label: int,
    classification_score: float,
    category: int,
) -> None:
    new_step = 2
    if classification_label == 0:
        new_step = 5
    query = """UPDATE autokmdb_news SET classification_label = %s,
               classification_score = %s, processing_step = %s, category = %s WHERE id = %s"""
    with connection.cursor() as cursor:
        cursor.execute(
            query, (classification_label, classification_score, new_step, category, id)
        )
    connection.commit()


def get_retries_from(connection: PooledMySQLConnection, date: str) -> list[dict]:
    query = """SELECT id, source_url AS url, source, newspaper_id FROM autokmdb_news WHERE skip_reason = 3 AND cre_time >= %s AND processing_step = 5 ORDER BY source DESC, mod_time DESC"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (date,))
        return cursor.fetchall()


def get_step_queue(
    connection: PooledMySQLConnection, step: int
) -> list[dict[str, Any]]:
    fields: dict[int, str] = {
        0: "clean_url AS url, source, newspaper_id",
        1: "title, description, text, source, newspaper_name, clean_url",
        2: "text",
        3: "text",
        4: "text",
    }
    query: str = f"""SELECT id, {fields[step]} FROM autokmdb_news
               WHERE processing_step = {step} ORDER BY source DESC, mod_time DESC LIMIT 50"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def get_download_queue(connection: PooledMySQLConnection) -> list[dict[str, Any]]:
    return get_step_queue(connection, 0)


def get_classification_queue(connection: PooledMySQLConnection) -> list[dict[str, Any]]:
    return get_step_queue(connection, 1)


def get_ner_queue(connection: PooledMySQLConnection) -> list[dict[str, Any]]:
    return get_step_queue(connection, 2)


def get_keyword_queue(connection: PooledMySQLConnection) -> list[dict[str, Any]]:
    return get_step_queue(connection, 3)


def get_human_queue(connection: PooledMySQLConnection) -> list[dict[str, Any]]:
    return get_step_queue(connection, 4)


@cached(cache=TTLCache(maxsize=32, ttl=3600))
def get_articles_by_day(
    start: str, end: str, newspaper_id: Optional[int] = None
) -> list[dict]:
    query = f"""
        SELECT 
            DATE(article_date) AS date, 
            SUM(CASE WHEN (processing_step = 5 AND annotation_label = 1) OR (processing_step = 5 AND annotation_label = 0) OR (classification_label = 1 AND processing_step = 4 AND annotation_label IS NULL AND (skip_reason = 0 OR skip_reason IS NULL)) THEN 1 ELSE 0 END) AS total_count, 
            SUM(CASE WHEN processing_step = 5 AND annotation_label = 1 THEN 1 ELSE 0 END) AS count_positive,
            SUM(CASE WHEN processing_step = 5 AND annotation_label = 0 THEN 1 ELSE 0 END) AS count_negative,
            SUM(CASE WHEN classification_label = 1 AND processing_step = 4 AND annotation_label IS NULL AND (skip_reason = 0 OR skip_reason IS NULL) THEN 1 ELSE 0 END) AS count_todo
        FROM 
            autokmdb_news 
        WHERE 
            article_date BETWEEN %s AND %s {"AND newspaper_id = %s" if newspaper_id else ""}
        GROUP BY 
            DATE(article_date) 
        ORDER BY 
            date
    """

    with connection_pool.get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                query, (start, end, newspaper_id) if newspaper_id else (start, end)
            )
            return cursor.fetchall()


def get_article_counts(
    connection: PooledMySQLConnection,
    domains: list[int],
    search_query="",
    start="2000-01-01",
    end="2050-01-01",
    skip_reason: int = -1,
) -> dict[str, int]:
    article_counts: dict[str, int] = {}
    start = start + " 00:00:00"
    end = end + " 23:59:59"

    domain_condition = ""
    if domains and domains[0] != -1 and isinstance(domains, list):
        domain_list: str = ",".join([str(domain) for domain in domains])
        domain_condition = f" AND n.newspaper_id IN ({domain_list})"

    search_condition = """
        AND (n.title LIKE %s OR n.description LIKE %s OR n.source_url LIKE %s)
    """

    date_condition = " AND n.article_date BETWEEN %s AND %s"

    skip_condition = ""
    if skip_reason != -1:
        skip_condition = " AND n.skip_reason = " + str(int(skip_reason))

    query = f"""
        SELECT 
            COUNT(CASE WHEN n.classification_label = 1 AND processing_step = 4 
                            AND n.annotation_label IS NULL 
                            AND (n.skip_reason = 0 OR n.skip_reason IS NULL) THEN id END) AS mixed,
            COUNT(CASE WHEN processing_step = 5 AND n.annotation_label = 1 THEN id END) AS positive,
            COUNT(CASE WHEN processing_step = 5 AND n.annotation_label = 0 THEN id END) AS negative,
            COUNT(CASE WHEN processing_step < 4 THEN id END) AS processing,
            COUNT(CASE WHEN processing_step >= 0 {skip_condition} THEN id END) AS all_status
        FROM autokmdb_news n
        WHERE 1=1
        {domain_condition}
        {search_condition if search_query != "%%" else ""}
        {date_condition}
    """

    search_tuple = (
        (search_query, search_query, search_query) if search_query != "%%" else ()
    )

    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            query,
            search_tuple + (start, end),
        )
        result = cursor.fetchone()
        if result:
            article_counts = {
                "mixed": result["mixed"],
                "positive": result["positive"],
                "negative": result["negative"],
                "processing": result["processing"],
                "all": result["all_status"],
            }

    return article_counts


def find_group_by_autokmdb_id(connection, autokmdb_id):
    query = """
SELECT group_id
FROM autokmdb_news_groups
WHERE autokmdb_news_id = %s;
"""
    with connection.cursor() as cursor:
        cursor.execute(query, (autokmdb_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
    return None


def add_article_group(connection, autokmdb_id) -> int:
    query = """
INSERT INTO autokmdb_news_groups (group_id, autokmdb_news_id, is_main)
VALUES (
    (SELECT new_group_id FROM (SELECT COALESCE(MAX(group_id) + 1, 1) AS new_group_id FROM autokmdb_news_groups) AS temp), -- Generate a new group_id using a derived table
    %s,
    TRUE
);
"""
    rowid = None
    with connection.cursor() as cursor:
        cursor.execute(query, (autokmdb_id,))
        rowid = cursor.lastrowid
    connection.commit()

    group_id = find_group_by_autokmdb_id(connection, autokmdb_id)

    query_set_group_id = """
UPDATE autokmdb_news SET group_id = %s WHERE id = %s;
"""
    with connection.cursor() as cursor:
        cursor.execute(query_set_group_id, (group_id, autokmdb_id))
    connection.commit()

    return rowid


def add_article_to_group(connection, autokmdb_id, group_id):
    query = """
INSERT INTO autokmdb_news_groups (group_id, autokmdb_news_id, is_main)
VALUES (%s, %s, FALSE);
"""
    with connection.cursor() as cursor:
        cursor.execute(query, (group_id, autokmdb_id))

    query_set_group_id = """
UPDATE autokmdb_news SET group_id = %s WHERE id = %s;
"""
    with connection.cursor() as cursor:
        cursor.execute(query_set_group_id, (group_id, autokmdb_id))
    connection.commit()


def pick_out_article(connetion, autokmdb_id, user_id):
    query = """
UPDATE autokmdb_news SET source = 1, group_id = NULL, mod_id = %s WHERE id = %s;
"""
    query_remove_from_group = """
DELETE FROM autokmdb_news_groups WHERE autokmdb_news_id = %s;
    """
    with connetion.cursor() as cursor:
        cursor.execute(query, (user_id, autokmdb_id))
        cursor.execute(query_remove_from_group, (autokmdb_id,))
    connetion.commit()


def get_article_persons_kmdb(cursor, id) -> list[dict[str, Any]]:
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


def get_article_institutions_kmdb(cursor, id) -> list[dict[str, Any]]:
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


def get_article_places_kmdb(cursor, id) -> list[dict[str, Any]]:
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


def get_article_others_kmdb(cursor, id) -> list[dict[str, Any]]:
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


def get_article_persons(cursor, id) -> list[dict]:
    query = """SELECT name, id, person_id AS db_id, person_name AS db_name, classification_score, classification_label, annotation_label, found_name, found_position FROM autokmdb_persons WHERE autokmdb_news_id = %s"""
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article_institutions(cursor, id) -> list[dict]:
    query = """SELECT name, id, institution_id AS db_id, institution_name AS db_name, classification_score, classification_label, annotation_label, found_name, found_position FROM autokmdb_institutions WHERE autokmdb_news_id = %s"""
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article_places(cursor, id) -> list[dict]:
    query = """SELECT name, id, place_id AS db_id, place_name AS db_name, classification_score, classification_label, annotation_label, found_name, found_position FROM autokmdb_places WHERE autokmdb_news_id = %s"""
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article_others(cursor, id) -> list[dict]:
    query = """SELECT name, id, other_id AS db_id, classification_score, classification_label, annotation_label FROM autokmdb_others WHERE autokmdb_news_id = %s"""
    cursor.execute(query, (id,))
    return cursor.fetchall()


def group_dicts_by_name(dict_list):
    groups = []
    visited = set()  # To keep track of the processed dictionaries
    for i, dict_i in enumerate(dict_list):
        if i in visited:
            continue  # Skip if this dictionary has already been grouped
        current_group = [dict_i]
        visited.add(i)
        for j, dict_j in enumerate(dict_list):
            if j in visited:
                continue
            # Check if either name is a substring of the other
            if dict_i["name"] in dict_j["name"] or dict_j["name"] in dict_i["name"]:
                current_group.append(dict_j)
                visited.add(j)
        groups.append(current_group)
    return groups


def map_entities(entities: list[dict]):
    def normalized_score(e):
        if e["classification_label"] == 1:
            return e["classification_score"]
        else:
            return 1 - e["classification_score"]

    def unnormalized_score(score):  # -> Any:
        label: Literal[1] | Literal[-1] = 1 if score > 0.5 else -1
        if label == 1:
            return score
        else:
            return 1 - score

    def avg(l):
        return sum(l) / len(l) if l else 0

    entity_map: dict[Optional[int], list] = defaultdict(list)
    for entity in entities:
        entity_map[entity["db_id"]].append(entity)
    map_non_db = group_dicts_by_name(entity_map[0])
    entity_list = []
    for db_id, entity_group in entity_map.items():
        annotation_label = None
        if any([e["annotation_label"] == 1 for e in entity_group]):
            annotation_label = 1
        elif any([e["annotation_label"] == 0 for e in entity_group]):
            annotation_label = 0
        if db_id is not None and db_id != 0:
            score = avg(
                [
                    normalized_score(e)
                    for e in entity_group
                    if "classification_label" in e
                ]
            )
            label = 1 if score > 0.5 else 0
            old_score = unnormalized_score(score)
            entity = {
                "db_id": db_id,
                "name": entity_group[0]["db_name"],
                "score": score,
                "classification_score": old_score,
                "classification_label": label,
                "annotation_label": annotation_label,
                "occurences": entity_group,
            }
            entity_list.append(entity)
    for entity_group in map_non_db:
        score = avg([normalized_score(e) for e in entity_group])
        label = 1 if score > 0.5 else 0
        old_score = unnormalized_score(score)
        entity = {
            "db_id": entity_group[0]["db_id"],
            "name": entity_group[0]["name"],
            "score": score,
            "classification_score": old_score,
            "classification_label": label,
            "annotation_label": annotation_label,
            "occurences": entity_group,
        }
        entity_list.append(entity)
    return entity_list


def get_article(connection: PooledMySQLConnection, id: int) -> dict[str, Any]:
    query = """SELECT n.id AS id, news_id, clean_url AS url, description, title, source, newspaper_name, newspaper_id, n.classification_score AS classification_score, n.classification_label AS classification_label, annotation_label, processing_step, skip_reason,
            n.text AS text, CONVERT_TZ(article_date, @@session.time_zone, '+00:00') as date, category, CONVERT_TZ(article_date, @@session.time_zone, '+00:00') as article_date, u.name AS mod_name, is_paywalled FROM autokmdb_news n LEFT JOIN users u ON n.mod_id = u.user_id WHERE id = %s
        """
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (id,))
        article: dict = cursor.fetchone()
        persons = get_article_persons(cursor, id)
        institutions = get_article_institutions(cursor, id)
        places = get_article_places(cursor, id)
        others = get_article_others(cursor, id)
        news_id = article["news_id"]
        if news_id:
            persons += get_article_persons_kmdb(cursor, news_id)
            institutions += get_article_institutions_kmdb(cursor, news_id)
            places += get_article_places_kmdb(cursor, news_id)
            others += get_article_others_kmdb(cursor, news_id)
        article["mapped_persons"] = map_entities(persons)
        article["mapped_institutions"] = map_entities(institutions)
        article["mapped_places"] = map_entities(places)
        article["others"] = others

        return article


def group_articles(articles):
    """
    This function is no longer needed as the get_articles function now handles grouping internally.
    Kept for backward compatibility but just returns articles as-is.
    """
    return articles


def get_articles(
    connection: PooledMySQLConnection,
    page: int,
    status: str,
    domains: list[int],
    search_query="",
    start="2000-01-01",
    end="2050-01-01",
    reverse=False,
    skip_reason: int = -1,
) -> Optional[tuple[int, list[dict[str, Any]]]]:
    start = start + " 00:00:00"
    end = end + " 23:59:59"

    # Build conditions once
    conditions = []
    params = []

    # Status condition
    if status == "mixed":
        conditions.append("n.classification_label = 1 AND processing_step = 4 AND n.annotation_label IS NULL AND COALESCE(n.skip_reason, 0) = 0")
    elif status == "positive":
        conditions.append("processing_step = 5 AND n.annotation_label = 1")
    elif status == "negative":
        conditions.append("processing_step = 5 AND n.annotation_label = 0")
    elif status == "processing":
        conditions.append("processing_step < 4")
    elif status == "all":
        conditions.append("processing_step >= 0")
    else:
        print("Invalid status provided!")
        return

    # Domain condition
    if domains and domains[0] != -1 and isinstance(domains, list):
        domain_list = ",".join([str(domain) for domain in domains])
        conditions.append(f"n.newspaper_id IN ({domain_list})")

    # Search condition
    if search_query != "%%":
        conditions.append("(n.title LIKE %s OR n.description LIKE %s OR n.source_url LIKE %s)")
        params.extend([search_query, search_query, search_query])

    # Date condition
    conditions.append("n.article_date BETWEEN %s AND %s")
    params.extend([start, end])

    # Skip reason condition
    if skip_reason != -1:
        conditions.append("n.skip_reason = %s")
        params.append(skip_reason)

    where_clause = " AND ".join(conditions)
    
    # Sort configuration
    sort_order = "ASC" if reverse else "DESC"
    sort_field = "n.source DESC, n.article_date" if status != "positive" else "n.article_date"

    with connection.cursor(dictionary=True) as cursor:
        # Use database-side deduplication with EXISTS subquery for better performance
        base_query = f"""
            SELECT 
                n.id, n.clean_url AS url, n.description, n.title, n.source, 
                n.newspaper_name, n.newspaper_id, n.classification_score, 
                n.classification_label, n.annotation_label, n.processing_step, 
                n.skip_reason, n.negative_reason,
                CONVERT_TZ(n.article_date, @@session.time_zone, '+00:00') AS date, 
                n.category, u.name AS mod_name, n.group_id
            FROM autokmdb_news n
            LEFT JOIN users u ON n.mod_id = u.user_id
            WHERE {where_clause}
              AND (n.group_id IS NULL 
                   OR n.id = (SELECT MIN(n2.id) 
                             FROM autokmdb_news n2 
                             WHERE n2.group_id = n.group_id))
            ORDER BY {sort_field} {sort_order}
        """

        # Count query - more efficient with the same deduplication logic
        count_query = f"""
            SELECT COUNT(*) as total_count 
            FROM autokmdb_news n
            WHERE {where_clause}
              AND (n.group_id IS NULL 
                   OR n.id = (SELECT MIN(n2.id) 
                             FROM autokmdb_news n2 
                             WHERE n2.group_id = n.group_id))
        """
        
        cursor.execute(count_query, params)
        count = cursor.fetchone()["total_count"]

        # Main query with pagination
        offset = (page - 1) * 10
        paginated_query = f"""
            {base_query}
            LIMIT 10 OFFSET {offset}
        """

        cursor.execute(paginated_query, params)
        main_articles = cursor.fetchall()

        # Get grouped articles for each main article that has a group_id
        articles_with_groups = []
        for article in main_articles:
            article['groupedArticles'] = []
            
            if article['group_id']:
                # Optimized grouped articles query
                group_query = """
                    SELECT 
                        n.id, n.clean_url AS url, n.title, n.description,
                        CONVERT_TZ(n.article_date, @@session.time_zone, '+00:00') AS date, 
                        n.newspaper_name, annotation_label, classification_label, negative_reason
                    FROM autokmdb_news n USE INDEX (idx_news_grouped_lookup)
                    WHERE n.group_id = %s AND n.id != %s
                    ORDER BY n.id
                """
                cursor.execute(group_query, (article['group_id'], article['id']))
                grouped_articles = cursor.fetchall()
                article['groupedArticles'] = grouped_articles
            
            articles_with_groups.append(article)

        return count, articles_with_groups


def force_accept_article(
    connection: PooledMySQLConnection, id: int, user_id: int
) -> None:
    query = """UPDATE autokmdb_news SET classification_label = 1, processing_step = 4, skip_reason = NULL, source = 1, mod_id = %s WHERE id = %s;"""
    with connection.cursor() as cursor:
        cursor.execute(query, (user_id, id))
    connection.commit()


def annote_negative(
    connection: PooledMySQLConnection, id: int, reason: int, user_id: int
) -> None:
    query = """UPDATE autokmdb_news SET annotation_label = 0, processing_step = 5, negative_reason = %s, mod_id = %s WHERE id = %s;"""
    query_id = """SELECT news_id FROM autokmdb_news WHERE id = %s;"""
    query_remove = """DELETE FROM news_news WHERE news_id = %s;"""
    query_remove_person = """DELETE FROM news_persons_link WHERE news_id = %s;"""
    query_remove_institution = (
        """DELETE FROM news_institutions_link WHERE news_id = %s;"""
    )
    query_remove_place = """DELETE FROM news_places_link WHERE news_id = %s;"""
    query_remove_other = """DELETE FROM news_others_link WHERE news_id = %s;"""
    query_remove_lang = """DELETE FROM news_lang WHERE news_id = %s;"""

    with connection.cursor() as cursor:
        cursor.execute(query_id, (id,))
        news_id: int = cursor.fetchone()[0]
        cursor.execute(
            query,
            (
                reason,
                user_id,
                id,
            ),
        )
        if news_id:
            cursor.execute(query_remove, (news_id,))
            cursor.execute(query_remove_person, (news_id,))
            cursor.execute(query_remove_institution, (news_id,))
            cursor.execute(query_remove_place, (news_id,))
            cursor.execute(query_remove_other, (news_id,))
            cursor.execute(query_remove_lang, (news_id,))
    connection.commit()


def create_person(connection: PooledMySQLConnection, name: str, user_id: int) -> int:
    logging.info("adding new person: " + name)
    query: str = (
        """INSERT INTO news_persons (status, name, cre_id, mod_id, import_id, cre_time, mod_time) VALUES (%s, %s, %s, %s, %s, %s, %s);"""
    )
    query_seo: str = (
        """INSERT INTO tags_seo_data (seo_name, tag_type, item_id) VALUES (%s, %s, %s);"""
    )
    query_check_person: str = """SELECT person_id FROM news_persons WHERE name = %s;"""

    current_datetime: datetime = datetime.now()
    cre_time: int = int(current_datetime.timestamp())

    with connection.cursor() as cursor:
        cursor.execute(query_check_person, (name,))
        result: Optional[list[int]] = cursor.fetchone()
        if result:
            person_id: int = result[0]
            logging.info(f"Person already exists with ID: {person_id}")
            return person_id

        cursor.execute(query, ("Y", name, user_id, user_id, 0, cre_time, cre_time))
        db_id: int = cursor.lastrowid
        cursor.execute(query_seo, (slugify(name), "persons", db_id))
    connection.commit()
    return db_id


def create_institution(
    connection: PooledMySQLConnection, name: str, user_id: int
) -> int:
    logging.info("adding new institution: " + name)
    query = """INSERT INTO news_institutions (status, name, cre_id, mod_id, import_id, cre_time, mod_time) VALUES (%s, %s, %s, %s, %s, %s, %s);"""
    query_seo = """INSERT INTO tags_seo_data (seo_name, tag_type, item_id) VALUES (%s, %s, %s);"""
    query_check_institution = (
        """SELECT institution_id FROM news_institutions WHERE name = %s;"""
    )

    current_datetime: datetime = datetime.now()
    cre_time = int(current_datetime.timestamp())

    with connection.cursor() as cursor:
        cursor.execute(query_check_institution, (name,))
        result: list[int] = cursor.fetchone()
        if result:
            institution_id: int = result[0]
            logging.info(f"Institution already exists with ID: {institution_id}")
            return institution_id

        cursor.execute(query, ("Y", name, user_id, user_id, 0, cre_time, cre_time))
        db_id: int = cursor.lastrowid
        cursor.execute(query_seo, (slugify(name), "institutions", db_id))
    connection.commit()
    return db_id


def get_article_annotation(connection: PooledMySQLConnection, news_id):
    get_annotation = """SELECT annotation_label FROM autokmdb_news WHERE id = %s;"""
    with connection.cursor() as cursor:
        cursor.execute(get_annotation, (news_id,))
        return cursor.fetchone()[0]


def setTags(cursor, news_id, persons, newspaper, institutions, places, others):
    def to_names(lst):
        result = []
        seen = set()
        for e in lst:
            if "db_name" in e and e["db_name"] and e["db_name"] not in seen:
                result.append(e["db_name"])
                seen.add(e["db_name"])
            elif "name" in e and e["name"] and e["name"] not in seen:
                result.append(e["name"])
                seen.add(e["name"])
            else:
                logging.warning(f"no names in: {e}")
        return result

    logging.info("setTags")
    names: list[str] = to_names(persons)
    names.append(newspaper)
    names += to_names(institutions)
    names += to_names(places)
    names += to_names(others)

    names_str: str = "|".join(names)

    tag_query = """SELECT tag_id FROM news_tags WHERE news_id = %s"""
    tag_update = """UPDATE news_tags SET names = %s WHERE tag_id = %s"""
    tag_insert = """INSERT INTO news_tags (names, news_id) VALUES (%s, %s)"""

    cursor.execute(tag_query, (news_id,))
    tag_id: list[Optional[int]] = cursor.fetchone()

    if tag_id and tag_id[0]:
        cursor.execute(
            tag_update,
            (
                names_str,
                news_id,
            ),
        )
        logging.info(
            f"updating tag_id={tag_id[0]} news_id={news_id} with text: {names_str}"
        )
    else:
        cursor.execute(
            tag_insert,
            (
                names_str,
                news_id,
            ),
        )
        logging.info(f"updating news_id={news_id} with text: {names_str}")


def annote_positive(
    connection: PooledMySQLConnection,
    id,
    source_url,
    source_url_string,
    title,
    description,
    text,
    persons,
    institutions,
    places,
    newspaper_id,
    newspaper_name,
    user_id,
    is_active,
    category,
    others,
    file_ids,
    pub_date,
):
    query_0 = """SELECT news_id FROM autokmdb_news WHERE id = %s LIMIT 1"""
    query_1 = """UPDATE autokmdb_news SET annotation_label = 1, processing_step = 5, news_id = %s, title = %s, description = %s, text = %s, mod_id = %s WHERE id = %s;"""
    query_2 = """INSERT INTO news_news (source_url, source_url_string, cre_time, mod_time, pub_time, cre_id, mod_id, status, news_type, news_rel) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, "D", "N");"""
    query_2_update = """UPDATE news_news
SET
    source_url = %s,
    source_url_string = %s,
    mod_time = %s,
    mod_id = %s,
    status = %s
WHERE
    news_id = %s;"""
    query_3 = """INSERT INTO news_lang (news_id, lang, name, teaser, articletext, alias, seo_url_default) VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    query_3_update = """UPDATE news_lang
SET 
    lang = %s, 
    name = %s, 
    teaser = %s, 
    articletext = %s, 
    alias = %s, 
    seo_url_default = %s
WHERE 
    news_id = %s;"""
    query_np = (
        """INSERT INTO news_newspapers_link (news_id, newspaper_id) VALUES (%s, %s);"""
    )
    query_np_update = """UPDATE news_newspapers_link
SET 
    newspaper_id = %s
WHERE 
    news_id = %s;"""
    query_cat = (
        """INSERT INTO news_categories_link (news_id, cid, head) VALUES (%s, %s, %s);"""
    )
    query_cat_update = (
        """UPDATE news_categories_link SET cid = %s, head = %s WHERE news_id = %s;"""
    )
    query_cat_autokmdb = (
        """UPDATE autokmdb_news SET category = %s WHERE news_id = %s;"""
    )
    query_p = """INSERT INTO news_persons_link (news_id, person_id) VALUES (%s, %s)"""
    delete_p = """DELETE FROM news_persons_link WHERE news_id = %s"""
    query_auto_p = """UPDATE autokmdb_persons SET annotation_label = 1 WHERE id = %s;"""
    query_i = """INSERT INTO news_institutions_link (news_id, institution_id) VALUES (%s, %s)"""
    delete_seo = """DELETE FROM seo_urls_data WHERE item_id = %s"""
    delete_i = """DELETE FROM news_institutions_link WHERE news_id = %s"""
    query_auto_i = (
        """UPDATE autokmdb_institutions SET annotation_label = 1 WHERE id = %s;"""
    )
    query_pl = """INSERT INTO news_places_link (news_id, place_id) VALUES (%s, %s)"""
    get_pl_parent = """SELECT parent_id FROM news_places WHERE place_id = %s;"""
    delete_pl = """DELETE FROM news_places_link WHERE news_id = %s"""
    query_auto_pl = """UPDATE autokmdb_places SET annotation_label = 1 WHERE id = %s;"""
    query_others = (
        """INSERT INTO news_others_link (news_id, other_id) VALUES (%s, %s)"""
    )
    delete_others = """DELETE FROM news_others_link WHERE news_id = %s;"""
    query_file = """INSERT INTO news_files_link (news_id, file_id) VALUES (%s, %s)"""
    delete_file = """DELETE FROM news_files_link WHERE news_id = %s;"""

    seo_query = """INSERT INTO seo_urls_data (seo_url, modul, action, item_id, lang) VALUES (%s, "news", "view", %s, "hu")"""

    current_datetime: datetime = datetime.now()
    cre_time = int(current_datetime.timestamp())

    with connection.cursor() as cursor:
        category_dict: dict[int | None, int] = {0: 5, 1: 6, 2: 7, None: 5}
        is_update = False
        alias: str = slugify(title)
        seo_url_default: str = "hirek/magyar-hirek/" + alias

        cursor.execute(query_0, (id,))
        news_id: int = cursor.fetchone()[0]

        if news_id:
            is_update = True
            logging.info("news_id exists: " + str(news_id))
            news_id = news_id
            cursor.execute(
                query_2_update,
                (
                    source_url,
                    source_url_string,
                    cre_time,
                    user_id,
                    "Y" if is_active else "N",
                    news_id,
                ),
            )
        else:
            cursor.execute(
                query_2,
                (
                    source_url,
                    source_url_string,
                    cre_time,
                    cre_time,
                    int(pub_date.timestamp()),
                    user_id,
                    user_id,
                    "Y" if is_active else "N",
                ),
            )
            news_id = cursor.lastrowid
        cursor.execute(query_1, (news_id, title, description, text, user_id, id))

        try:
            cursor.execute(delete_seo, (news_id,))
        except Exception as e:
            pass

        cursor.execute(seo_query, (seo_url_default, news_id))

        if is_update:
            cursor.execute(
                query_3_update,
                (
                    "hu",
                    title,
                    description,
                    text.replace("\n", "<br>"),
                    alias,
                    seo_url_default,
                    news_id,
                ),
            )
        else:
            cursor.execute(
                query_3,
                (
                    news_id,
                    "hu",
                    title,
                    description,
                    text.replace("\n", "<br>"),
                    alias,
                    seo_url_default,
                ),
            )

        for person in persons:
            if ("db_id" not in person or not person["db_id"]) and person["name"]:
                db_id: int = create_person(connection, person["name"], user_id)
                person["db_id"] = db_id
        for institution in institutions:
            if ("db_id" not in institution or not institution["db_id"]) and institution[
                "name"
            ]:
                db_id = create_institution(connection, institution["name"], user_id)
                institution["db_id"] = db_id

        if is_update:
            cursor.execute(query_np_update, (newspaper_id, news_id))
        else:
            cursor.execute(query_np, (news_id, newspaper_id))

        if is_update:
            cursor.execute(query_cat_update, (category_dict[category], "Y", news_id))
        else:
            cursor.execute(query_cat, (news_id, category_dict[category], "Y"))
        cursor.execute(query_cat_autokmdb, (news_id, category))

        done_person_ids = set()
        done_institution_ids = set()
        done_place_ids = set()

        if is_update:
            cursor.execute(delete_p, (news_id,))
        for person in persons:
            if person["db_id"] not in done_person_ids:
                cursor.execute(query_p, (news_id, person["db_id"]))
                done_person_ids.add(person["db_id"])
            if "id" in person and isinstance(person["id"], int):
                cursor.execute(query_auto_p, (person["id"],))
        if is_update:
            cursor.execute(delete_i, (news_id,))
        for institution in institutions:
            if institution["db_id"] not in done_institution_ids:
                cursor.execute(query_i, (news_id, institution["db_id"]))
                done_institution_ids.add(institution["db_id"])
            if "id" in institution and isinstance(institution["id"], int):
                cursor.execute(query_auto_i, (institution["id"],))
        if is_update:
            cursor.execute(delete_pl, (news_id,))
        for place in places:
            if place["db_id"] not in done_place_ids:
                cursor.execute(query_pl, (news_id, place["db_id"]))
                done_place_ids.add(place["db_id"])
                cursor.execute(get_pl_parent, (place["db_id"],))
                parent_id = cursor.fetchone()
                if parent_id and parent_id[0] and parent_id[0] not in done_place_ids:
                    cursor.execute(query_pl, (news_id, parent_id[0]))
                    done_place_ids.add(parent_id[0])
            if "id" in place and isinstance(place["id"], int):
                cursor.execute(query_auto_pl, (place["id"],))

        if is_update:
            cursor.execute(delete_others, (news_id,))
        for other in others:
            cursor.execute(query_others, (news_id, other["db_id"]))

        if is_update:
            cursor.execute(delete_file, (news_id,))
        for file_id in file_ids:
            cursor.execute(query_file, (news_id, file_id))

        setTags(cursor, news_id, persons, newspaper_name, institutions, places, others)

    connection.commit()


def save_ner_step(connection: PooledMySQLConnection, id):
    query = """UPDATE autokmdb_news SET processing_step = 3 WHERE id = %s;"""
    with connection.cursor() as cursor:
        cursor.execute(query, (id,))
    connection.commit()


def save_keyword_step(connection: PooledMySQLConnection, id):
    query = """UPDATE autokmdb_news SET processing_step = 4 WHERE id = %s;"""
    with connection.cursor() as cursor:
        cursor.execute(query, (id,))
    connection.commit()


def get_rss_urls(connection: PooledMySQLConnection):
    query = """SELECT newspaper_id as id, name, rss_url FROM news_newspapers WHERE status = "Y";"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return cursor.fetchall()


@cache
def get_keyword_synonyms(connection: PooledMySQLConnection) -> list[dict]:
    query = """SELECT synonym, name, db_id FROM autokmdb_keyword_synonyms"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return cursor.fetchall()


def update_session(
    connection: PooledMySQLConnection, session_id: Optional[str], unix_timestamp: int
):
    query = """UPDATE users_sessions SET session_expires = %s WHERE session_id = %s"""
    dt: datetime = datetime.fromtimestamp(unix_timestamp)
    new_dt: datetime = dt + timedelta(minutes=30)
    new_unix_timestamp = int(new_dt.timestamp())
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (new_unix_timestamp, session_id))
    connection.commit()


def validate_session(connection: PooledMySQLConnection, session_id: Optional[str]):
    if "NO_LOGIN" in os.environ:
        return True
    query = """SELECT * FROM users_sessions WHERE session_id = %s;"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (session_id,))
        session: Optional[dict] = cursor.fetchone()
    if session is None or session["registered"] == 0:
        return None

    update_session(connection, session_id, session["session_expires"])

    return session["registered"]


def get_roles(connection: PooledMySQLConnection, session_id: int):
    query = """SELECT * FROM users_sessions WHERE session_id = %s;"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (session_id,))
    session: dict = cursor.fetchone()
    if session is None or session["registered"] == 0:
        return []

    user_id: int = session["registered"]

    query_u = """SELECT * FROM users_modul_rights WHERE user_id = %s;"""

    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query_u, (user_id,))

    roles: list[dict[str, Any]] = [
        {
            "modul_name": r["modul_name"],
            "action_name": r["action_name"],
            "action_right": r["action_right"],
        }
        for r in cursor.fetchall()
    ]

    return roles
