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
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_others
                (autokmdb_news_id, other_id, name, classification_score, classification_label, version_number)
                VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(
            query,
            (
                autokmdb_news_id,
                other_id,
                name,
                classification_score,
                classification_label,
                VERSION_NUMBER,
            ),
        )
    connection.commit()


def add_auto_files(
    connection: PooledMySQLConnection,
    autokmdb_news_id: int,
    files_id: int,
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    with connection.cursor() as cursor:
        query = """INSERT INTO autokmdb_files
                (autokmdb_news_id, files_id, name, classification_score, classification_label, version_number)
                VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(
            query,
            (
                autokmdb_news_id,
                files_id,
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
    newspaper_id: Optional[int] = None
) -> list[dict]:
    newspaper_condition = "WHERE newspaper_id = %s" if newspaper_id else ""
    params = [newspaper_id] if newspaper_id else []
    
    with connection_pool.get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            # Single optimized query using conditional aggregation
            query = f"""
                SELECT 
                    DATE(article_date) AS date,
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN processing_step = 5 AND annotation_label = 1 THEN 1 ELSE 0 END) AS count_positive,
                    SUM(CASE WHEN processing_step = 5 AND annotation_label = 0 AND negative_reason = 0 THEN 1 ELSE 0 END) AS count_negative_0,
                    SUM(CASE WHEN processing_step = 5 AND annotation_label = 0 AND negative_reason = 1 THEN 1 ELSE 0 END) AS count_negative_1,
                    SUM(CASE WHEN processing_step = 5 AND annotation_label = 0 AND negative_reason = 2 THEN 1 ELSE 0 END) AS count_negative_2,
                    SUM(CASE WHEN processing_step = 5 AND annotation_label = 0 AND negative_reason = 3 THEN 1 ELSE 0 END) AS count_negative_3,
                    SUM(CASE WHEN processing_step = 5 AND annotation_label = 0 AND negative_reason = 100 THEN 1 ELSE 0 END) AS count_negative_100,
                    SUM(CASE WHEN classification_label = 1 AND processing_step = 4 
                             AND annotation_label IS NULL AND COALESCE(skip_reason, 0) = 0 THEN 1 ELSE 0 END) AS count_todo
                FROM autokmdb_news 
                {newspaper_condition}
                GROUP BY DATE(article_date)
                ORDER BY date
            """
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Calculate derived fields
            final_results = []
            for row in results:
                count_negative = (row["count_negative_0"] + row["count_negative_1"] + 
                                row["count_negative_2"] + row["count_negative_3"] + 
                                row["count_negative_100"])
                
                final_results.append({
                    "date": row["date"],
                    "total_count": row["count_positive"] + count_negative + row["count_todo"],
                    "count_positive": row["count_positive"],
                    "count_negative": count_negative,
                    "count_negative_0": row["count_negative_0"],  # nem releváns
                    "count_negative_1": row["count_negative_1"],  # átvett
                    "count_negative_2": row["count_negative_2"],  # külföldi
                    "count_negative_3": row["count_negative_3"],  # már szerepel
                    "count_negative_100": row["count_negative_100"],  # egyéb
                    "count_todo": row["count_todo"]
                })
            
            return final_results

# Add these indexes to your database for optimal performance:
# CREATE INDEX idx_autokmdb_news_article_date ON autokmdb_news (article_date);
# CREATE INDEX idx_autokmdb_news_processing_annotation ON autokmdb_news (processing_step, annotation_label, negative_reason);
# CREATE INDEX idx_autokmdb_news_classification_step ON autokmdb_news (classification_label, processing_step, annotation_label, skip_reason);
# CREATE INDEX idx_autokmdb_news_newspaper_date ON autokmdb_news (newspaper_id, article_date);
# CREATE INDEX idx_autokmdb_news_compound ON autokmdb_news (article_date, newspaper_id, processing_step, annotation_label, classification_label);


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


def get_article_others(cursor, id) -> list[dict]:
    query = """SELECT name, id, other_id AS db_id, classification_score, classification_label, annotation_label FROM autokmdb_others WHERE autokmdb_news_id = %s"""
    cursor.execute(query, (id,))
    return cursor.fetchall()


def get_article_files(cursor, id) -> list[dict]:
    query = """SELECT name, id, files_id AS db_id, classification_score, classification_label, annotation_label FROM autokmdb_files WHERE autokmdb_news_id = %s"""
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
        annotation_label = 0
        if any([e["annotation_label"] == 1 for e in entity_group]):
            annotation_label = 1

        entity = {
            "db_id": entity_group[0]["db_id"],
            "name": entity_group[0]["name"],
            "score": score,
            "classification_score": old_score,
            "classification_label": label,
            "annotation_label": entity_group[0]["annotation_label"],
            "occurences": entity_group,
        }
        entity_list.append(entity)
    return entity_list


def get_article(connection: PooledMySQLConnection, id: int) -> dict[str, Any]:
    # Single comprehensive query to get article with all entity data
    query = """
        SELECT 
            n.id AS id, n.news_id, n.clean_url AS url, n.description, n.title, n.source, 
            n.newspaper_name, n.newspaper_id, n.classification_score, n.classification_label, 
            n.annotation_label, n.processing_step, n.skip_reason, n.text, 
            CONVERT_TZ(n.article_date, @@session.time_zone, '+00:00') as date, 
            n.category, CONVERT_TZ(n.article_date, @@session.time_zone, '+00:00') as article_date, 
            u.name AS mod_name, n.is_paywalled,
            
            -- Person data
            ap.id as person_auto_id, ap.name as person_name, ap.person_id as person_db_id, 
            ap.person_name as person_db_name, ap.classification_score as person_classification_score,
            ap.classification_label as person_classification_label, ap.annotation_label as person_annotation_label,
            ap.found_name as person_found_name, ap.found_position as person_found_position,
            
            -- Institution data  
            ai.id as institution_auto_id, ai.name as institution_name, ai.institution_id as institution_db_id,
            ai.institution_name as institution_db_name, ai.classification_score as institution_classification_score,
            ai.classification_label as institution_classification_label, ai.annotation_label as institution_annotation_label,
            ai.found_name as institution_found_name, ai.found_position as institution_found_position,
            
            -- Place data
            apl.id as place_auto_id, apl.name as place_name, apl.place_id as place_db_id,
            apl.place_name as place_db_name, apl.classification_score as place_classification_score,
            apl.classification_label as place_classification_label, apl.annotation_label as place_annotation_label,
            apl.found_name as place_found_name, apl.found_position as place_found_position,
            
            -- Other data
            ao.id as other_auto_id, ao.name as other_name, ao.other_id as other_db_id,
            ao.classification_score as other_classification_score, ao.classification_label as other_classification_label,
            ao.annotation_label as other_annotation_label
            
        FROM autokmdb_news n 
        LEFT JOIN users u ON n.mod_id = u.user_id
        LEFT JOIN autokmdb_persons ap ON n.id = ap.autokmdb_news_id
        LEFT JOIN autokmdb_institutions ai ON n.id = ai.autokmdb_news_id  
        LEFT JOIN autokmdb_places apl ON n.id = apl.autokmdb_news_id
        LEFT JOIN autokmdb_others ao ON n.id = ao.autokmdb_news_id
        LEFT JOIN autokmdb_files ao ON n.id = ao.autokmdb_news_id
        WHERE n.id = %s
    """
    
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (id,))
        rows = cursor.fetchall()
        
        if not rows:
            return {}
            
        # Extract article data from first row (all rows have same article data)
        article_data = rows[0]
        article = {
            "id": article_data["id"],
            "news_id": article_data["news_id"],
            "url": article_data["url"],
            "description": article_data["description"],
            "title": article_data["title"],
            "source": article_data["source"],
            "newspaper_name": article_data["newspaper_name"],
            "newspaper_id": article_data["newspaper_id"],
            "classification_score": article_data["classification_score"],
            "classification_label": article_data["classification_label"],
            "annotation_label": article_data["annotation_label"],
            "processing_step": article_data["processing_step"],
            "skip_reason": article_data["skip_reason"],
            "text": article_data["text"],
            "date": article_data["date"],
            "category": article_data["category"],
            "article_date": article_data["article_date"],
            "mod_name": article_data["mod_name"],
            "is_paywalled": article_data["is_paywalled"]
        }
        
        # Efficiently collect entities from joined data
        persons = []
        institutions = []
        places = []
        others = []
        files = []
        
        # Process all rows to extract entity data
        seen_persons = set()
        seen_institutions = set()
        seen_places = set()
        seen_others = set()
        seen_files = set()
        
        for row in rows:
            # Process persons
            if row["person_auto_id"] and row["person_auto_id"] not in seen_persons:
                persons.append({
                    "id": row["person_auto_id"],
                    "name": row["person_name"],
                    "db_id": row["person_db_id"],
                    "db_name": row["person_db_name"],
                    "classification_score": row["person_classification_score"],
                    "classification_label": row["person_classification_label"],
                    "annotation_label": row["person_annotation_label"],
                    "found_name": row["person_found_name"],
                    "found_position": row["person_found_position"]
                })
                seen_persons.add(row["person_auto_id"])
                
            # Process institutions
            if row["institution_auto_id"] and row["institution_auto_id"] not in seen_institutions:
                institutions.append({
                    "id": row["institution_auto_id"],
                    "name": row["institution_name"],
                    "db_id": row["institution_db_id"],
                    "db_name": row["institution_db_name"],
                    "classification_score": row["institution_classification_score"],
                    "classification_label": row["institution_classification_label"],
                    "annotation_label": row["institution_annotation_label"],
                    "found_name": row["institution_found_name"],
                    "found_position": row["institution_found_position"]
                })
                seen_institutions.add(row["institution_auto_id"])
                
            # Process places
            if row["place_auto_id"] and row["place_auto_id"] not in seen_places:
                places.append({
                    "id": row["place_auto_id"],
                    "name": row["place_name"],
                    "db_id": row["place_db_id"],
                    "db_name": row["place_db_name"],
                    "classification_score": row["place_classification_score"],
                    "classification_label": row["place_classification_label"],
                    "annotation_label": row["place_annotation_label"],
                    "found_name": row["place_found_name"],
                    "found_position": row["place_found_position"]
                })
                seen_places.add(row["place_auto_id"])
                
            # Process others
            if row["other_auto_id"] and row["other_auto_id"] not in seen_others:
                others.append({
                    "id": row["other_auto_id"],
                    "name": row["other_name"],
                    "db_id": row["other_db_id"],
                    "classification_score": row["other_classification_score"],
                    "classification_label": row["other_classification_label"],
                    "annotation_label": row["other_annotation_label"]
                })
                seen_others.add(row["other_auto_id"])
            
            # Process files
            if row["files_id"] and row["files_id"] not in seen_files:
                files.append({
                    "id": row["files_id"],
                    "name": row["name"],
                    "db_id": row["files_id"],
                    "classification_score": row["classification_score"],
                    "classification_label": row["classification_label"],
                    "annotation_label": row["annotation_label"]
                })
                seen_files.add(row["files_id"])
        
        # Handle KMDB entities if news_id exists
        news_id = article["news_id"]
        if news_id:
            # Single query to get all KMDB entities for this article
            kmdb_query = """
                SELECT 
                    'person' as entity_type, pl.person_id as entity_id
                FROM news_persons_link pl
                WHERE pl.news_id = %s
                UNION ALL
                SELECT 
                    'institution' as entity_type, il.institution_id as entity_id
                FROM news_institutions_link il
                WHERE il.news_id = %s
                UNION ALL
                SELECT 
                    'place' as entity_type, pll.place_id as entity_id
                FROM news_places_link pll
                WHERE pll.news_id = %s
                UNION ALL
                SELECT 
                    'other' as entity_type, ol.other_id as entity_id
                FROM news_others_link ol
                WHERE ol.news_id = %s
            """
            
            cursor.execute(kmdb_query, (news_id, news_id, news_id, news_id))
            kmdb_entities = cursor.fetchall()
            
            # Process KMDB entities efficiently using cached lookups
            for entity in kmdb_entities:
                entity_type = entity["entity_type"]
                entity_id = entity["entity_id"]
                
                if entity_type == "person" and entity_id in all_persons_by_id:
                    persons.append({
                        "annotation_label": 1,
                        "db_id": entity_id,
                        "name": all_persons_by_id[entity_id],
                        "db_name": all_persons_by_id[entity_id]
                    })
                elif entity_type == "institution" and entity_id in all_institutions_by_id:
                    institutions.append({
                        "annotation_label": 1,
                        "db_id": entity_id,
                        "name": all_institutions_by_id[entity_id],
                        "db_name": all_institutions_by_id[entity_id]
                    })
                elif entity_type == "place" and entity_id in all_places_by_id:
                    places.append({
                        "annotation_label": 1,
                        "db_id": entity_id,
                        "name": all_places_by_id[entity_id],
                        "db_name": all_places_by_id[entity_id]
                    })
                elif entity_type == "other" and entity_id in all_others_by_id:
                    others.append({
                        "annotation_label": 1,
                        "db_id": entity_id,
                        "name": all_others_by_id[entity_id],
                        "db_name": all_others_by_id[entity_id]
                    })
                elif entity_type == "file" and entity_id in all_files_by_id:
                    files.append({
                        "annotation_label": 1,
                        "db_id": entity_id,
                        "name": all_files_by_id[entity_id],
                        "db_name": all_files_by_id[entity_id]
                    })
        
        # Map entities efficiently
        article["mapped_persons"] = map_entities(persons)
        article["mapped_institutions"] = map_entities(institutions)
        article["mapped_places"] = map_entities(places)
        article["others"] = others
        article["files"] = files
        
        return article


def group_articles(articles):
    """
    This function is no longer needed as the get_articles function now handles grouping internally.
    Kept for backward compatibility but just returns articles as-is.
    """
    return articles


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
        conditions.append(
            "n.classification_label = 1 AND n.processing_step = 4 AND n.annotation_label IS NULL AND COALESCE(n.skip_reason, 0) = 0"
        )
    elif status == "positive":
        conditions.append("n.processing_step = 5 AND n.annotation_label = 1")
    elif status == "negative":
        conditions.append("n.processing_step = 5 AND n.annotation_label = 0")
    elif status == "processing":
        conditions.append("n.processing_step < 4")
    elif status == "all":
        conditions.append("n.processing_step >= 0")
    else:
        print("Invalid status provided!")
        return

    # Domain condition
    if domains and domains[0] != -1 and isinstance(domains, list):
        domain_list = ",".join([str(domain) for domain in domains])
        conditions.append(f"n.newspaper_id IN ({domain_list})")

    # Search condition
    if search_query != "%%":
        conditions.append(
            "(n.title LIKE %s OR n.description LIKE %s OR n.source_url LIKE %s)"
        )
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
    sort_field = (
        "main.source DESC, main.article_date"
        if status != "positive"
        else "main.article_date"
    )

    with connection.cursor(dictionary=True) as cursor:
        # Step 1: Find all group_ids that have at least one matching article
        qualifying_groups_query = f"""
            SELECT DISTINCT n.group_id
            FROM autokmdb_news n
            WHERE n.group_id IS NOT NULL AND {where_clause}
        """

        cursor.execute(qualifying_groups_query, params)
        qualifying_groups = [row["group_id"] for row in cursor.fetchall()]

        # Step 2: Build the main query with optimized logic
        if qualifying_groups:
            groups_list = ",".join(map(str, qualifying_groups))
            group_condition = f"main.group_id IN ({groups_list})"
        else:
            group_condition = "FALSE"

        # Main query: get articles that either match directly OR are main articles of qualifying groups
        base_query = f"""
            SELECT 
                main.id, main.clean_url AS url, main.description, main.title, main.source, 
                main.newspaper_name, main.newspaper_id, main.classification_score, 
                main.classification_label, main.annotation_label, main.processing_step, 
                main.skip_reason, main.negative_reason,
                CONVERT_TZ(main.article_date, @@session.time_zone, '+00:00') AS date, 
                main.category, u.name AS mod_name, main.group_id
            FROM autokmdb_news main
            LEFT JOIN users u ON main.mod_id = u.user_id
            WHERE (main.group_id IS NULL 
                   OR main.id = (SELECT MIN(n3.id) FROM autokmdb_news n3 WHERE n3.group_id = main.group_id))
              AND (
                  -- Direct match for ungrouped articles or main articles
                  (main.group_id IS NULL AND ({where_clause.replace('n.', 'main.')}))
                  OR
                  -- Main article of a qualifying group
                  (main.group_id IS NOT NULL AND {group_condition})
              )
            ORDER BY {sort_field} {sort_order}
        """

        # Count query with the same logic
        count_query = f"""
            SELECT COUNT(*) as total_count 
            FROM autokmdb_news main
            WHERE (main.group_id IS NULL 
                   OR main.id = (SELECT MIN(n3.id) FROM autokmdb_news n3 WHERE n3.group_id = main.group_id))
              AND (
                  -- Direct match for ungrouped articles or main articles
                  (main.group_id IS NULL AND ({where_clause.replace('n.', 'main.')}))
                  OR
                  -- Main article of a qualifying group
                  (main.group_id IS NOT NULL AND {group_condition})
              )
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

        # Step 3: Bulk fetch all grouped articles for all groups on this page
        articles_with_groups = []
        if main_articles:
            # Get all group_ids that have groups on this page
            page_group_ids = [
                article["group_id"] for article in main_articles if article["group_id"]
            ]

            if page_group_ids:
                # Single query to get all grouped articles for all groups on this page
                groups_list_page = ",".join(map(str, page_group_ids))
                bulk_group_query = f"""
                    SELECT 
                        n.group_id,
                        n.id, n.clean_url AS url, n.title, n.description,
                        CONVERT_TZ(n.article_date, @@session.time_zone, '+00:00') AS date, 
                        n.newspaper_name, annotation_label, classification_label, negative_reason
                    FROM autokmdb_news n 
                    WHERE n.group_id IN ({groups_list_page}) 
                      AND n.id NOT IN ({",".join(str(article['id']) for article in main_articles if article['group_id'])})
                    ORDER BY n.group_id, n.id
                """

                cursor.execute(bulk_group_query)
                all_grouped_articles = cursor.fetchall()

                # Group the results by group_id for easy lookup
                grouped_by_group_id = {}
                for article in all_grouped_articles:
                    group_id = article["group_id"]
                    if group_id not in grouped_by_group_id:
                        grouped_by_group_id[group_id] = []
                    article_copy = {k: v for k, v in article.items()}
                    grouped_by_group_id[group_id].append(article_copy)

        # Step 4: Assign grouped articles to their main articles
        for article in main_articles:
            if article["group_id"] and page_group_ids:
                article["groupedArticles"] = grouped_by_group_id.get(
                    article["group_id"], []
                )
            else:
                article["groupedArticles"] = []

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
    tag_result = cursor.fetchone()

    if tag_result and tag_result.get("tag_id"):
        tag_id = tag_result["tag_id"]
        cursor.execute(
            tag_update,
            (
                names_str,
                tag_id,
            ),
        )
        logging.info(
            f"updating tag_id={tag_id} news_id={news_id} with text: {names_str}"
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
    """
        This function annotates an article as positive, updating or creating the necessary records in the database.
        It handles both the creation of new articles and the updating of existing ones, ensuring that all related entities are properly linked.
        It should remove entities that are not present in the new data. It should update the article's status, source URL, and other metadata.
    """

    # Pre-calculate all constants
    current_datetime = datetime.now()
    cre_time = int(current_datetime.timestamp())
    category_dict = {0: 5, 1: 6, 2: 7, None: 5}
    alias = slugify(title)
    seo_url_default = "hirek/magyar-hirek/" + alias
    processed_text = text.replace("\n", "<br>")
    pub_timestamp = int(pub_date.timestamp())
    status_flag = "Y" if is_active else "N"
    
    # Prepare entity collections
    persons_to_create = [p for p in persons if ("db_id" not in p or not p["db_id"]) and p.get("name")]
    institutions_to_create = [i for i in institutions if ("db_id" not in i or not i["db_id"]) and i.get("name")]

    with connection.cursor(dictionary=True) as cursor:
        # Single query to get all initial data needed
        cursor.execute("SELECT news_id FROM autokmdb_news WHERE id = %s", (id,))
        result = cursor.fetchone()
        news_id = result["news_id"] if result else None
        is_update = bool(news_id)

        # Batch check existing entities in single transaction
        existing_persons = {}
        existing_institutions = {}
        
        if persons_to_create:
            person_names = [p["name"] for p in persons_to_create]
            placeholders = ",".join(["%s"] * len(person_names))
            cursor.execute(
                f"SELECT person_id, name FROM news_persons WHERE name IN ({placeholders})",
                person_names
            )
            existing_persons = {row["name"]: row["person_id"] for row in cursor.fetchall()}

        if institutions_to_create:
            institution_names = [i["name"] for i in institutions_to_create]
            placeholders = ",".join(["%s"] * len(institution_names))
            cursor.execute(
                f"SELECT institution_id, name FROM news_institutions WHERE name IN ({placeholders})",
                institution_names
            )
            existing_institutions = {row["name"]: row["institution_id"] for row in cursor.fetchall()}

        # Create missing entities (still needs individual calls for SEO)
        for person in persons_to_create:
            if person["name"] in existing_persons:
                person["db_id"] = existing_persons[person["name"]]
            else:
                person["db_id"] = create_person(connection, person["name"], user_id)
                all_persons_by_id[person["db_id"]] = person["name"]

        for institution in institutions_to_create:
            if institution["name"] in existing_institutions:
                institution["db_id"] = existing_institutions[institution["name"]]
            else:
                institution["db_id"] = create_institution(connection, institution["name"], user_id)
                all_institutions_by_id[institution["db_id"]] = institution["name"]

        # Handle main news record operations
        if is_update:
            # Consolidated UPDATE for existing records
            cursor.execute(
                """UPDATE news_news SET source_url = %s, source_url_string = %s, 
                   mod_time = %s, mod_id = %s, status = %s WHERE news_id = %s""",
                (source_url, source_url_string, cre_time, user_id, status_flag, news_id)
            )
            
            # Clear existing links before adding new ones
            delete_queries = [
                ("DELETE FROM news_persons_link WHERE news_id = %s", "persons"),
                ("DELETE FROM news_institutions_link WHERE news_id = %s", "institutions"),
                ("DELETE FROM news_places_link WHERE news_id = %s", "places"),
                ("DELETE FROM news_others_link WHERE news_id = %s", "others"),
                ("DELETE FROM news_files_link WHERE news_id = %s", "files")
            ]
            
            for query, table_name in delete_queries:
                try:
                    cursor.execute(query, (news_id,))
                    rows_affected = cursor.rowcount
                    logging.info(f"Deleted {rows_affected} rows from {table_name} for news_id {news_id}")
                except Exception as e:
                    logging.error(f"Error deleting from {table_name}: {e}")
                    # Re-raise to prevent duplicate key errors
                    raise
            
        else:
            # Create new news record
            cursor.execute(
                """INSERT INTO news_news (source_url, source_url_string, cre_time, 
                   mod_time, pub_time, cre_id, mod_id, status, news_type, news_rel) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'D', 'N')""",
                (source_url, source_url_string, cre_time, cre_time, pub_timestamp, 
                 user_id, user_id, status_flag)
            )
            news_id = cursor.lastrowid

        # Batch update autokmdb_news with category
        cursor.execute(
            """UPDATE autokmdb_news SET annotation_label = 1, processing_step = 5, 
               news_id = %s, title = %s, description = %s, text = %s, mod_id = %s, category = %s 
               WHERE id = %s""",
            (news_id, title, description, text, user_id, category, id)
        )

        # Use REPLACE for SEO URLs (more efficient than DELETE + INSERT)
        cursor.execute(
            """REPLACE INTO seo_urls_data (seo_url, modul, action, item_id, lang) 
               VALUES (%s, 'news', 'view', %s, 'hu')""",
            (seo_url_default, news_id)
        )

        # Handle language data
        if is_update:
            cursor.execute(
                """UPDATE news_lang SET lang = 'hu', name = %s, teaser = %s, 
                   articletext = %s, alias = %s, seo_url_default = %s WHERE news_id = %s""",
                (title, description, processed_text, alias, seo_url_default, news_id)
            )
        else:
            cursor.execute(
                """INSERT INTO news_lang (news_id, lang, name, teaser, articletext, alias, seo_url_default) 
                   VALUES (%s, 'hu', %s, %s, %s, %s, %s)""",
                (news_id, title, description, processed_text, alias, seo_url_default)
            )

        # Handle newspaper and category links
        if is_update:
            cursor.execute(
                "UPDATE news_newspapers_link SET newspaper_id = %s WHERE news_id = %s",
                (newspaper_id, news_id)
            )
            cursor.execute(
                "UPDATE news_categories_link SET cid = %s, head = 'Y' WHERE news_id = %s",
                (category_dict[category], news_id)
            )
        else:
            cursor.execute(
                "INSERT INTO news_newspapers_link (news_id, newspaper_id) VALUES (%s, %s)",
                (news_id, newspaper_id)
            )
            cursor.execute(
                "INSERT INTO news_categories_link (news_id, cid, head) VALUES (%s, %s, 'Y')",
                (news_id, category_dict[category])
            )

        # Efficiently collect unique entity IDs and prepare batch operations
        unique_person_ids = set()
        unique_institution_ids = set()
        unique_place_ids = set()
        
        person_updates = []
        institution_updates = []
        place_updates = []
        
        for person in persons:
            if person.get("db_id"):
                unique_person_ids.add(person["db_id"])
            if "id" in person and isinstance(person["id"], int):
                person_updates.append(person["id"])

        for institution in institutions:
            if institution.get("db_id"):
                unique_institution_ids.add(institution["db_id"])
            if "id" in institution and isinstance(institution["id"], int):
                institution_updates.append(institution["id"])

        for place in places:
            if place.get("db_id"):
                unique_place_ids.add(place["db_id"])
            if "id" in place and isinstance(place["id"], int):
                place_updates.append(place["id"])

        # Get parent places in batch if needed
        if unique_place_ids:
            place_list = list(unique_place_ids)
            placeholders = ",".join(["%s"] * len(place_list))
            cursor.execute(
                f"SELECT parent_id FROM news_places WHERE place_id IN ({placeholders}) AND parent_id IS NOT NULL",
                place_list
            )
            for row in cursor.fetchall():
                if row["parent_id"]:
                    unique_place_ids.add(row["parent_id"])

        # Prepare all batch insert operations
        batch_inserts = []
        
        if unique_person_ids:
            person_links = [(news_id, pid) for pid in unique_person_ids]
            batch_inserts.append(("INSERT INTO news_persons_link (news_id, person_id) VALUES (%s, %s)", person_links))
            
        if unique_institution_ids:
            institution_links = [(news_id, iid) for iid in unique_institution_ids]
            batch_inserts.append(("INSERT INTO news_institutions_link (news_id, institution_id) VALUES (%s, %s)", institution_links))
            
        if unique_place_ids:
            place_links = [(news_id, pid) for pid in unique_place_ids]
            batch_inserts.append(("INSERT INTO news_places_link (news_id, place_id) VALUES (%s, %s)", place_links))
            
        if others:
            other_links = [(news_id, other["db_id"]) for other in others if other.get("db_id")]
            if other_links:
                batch_inserts.append(("INSERT INTO news_others_link (news_id, other_id) VALUES (%s, %s)", other_links))
            
        if file_ids:
            file_links = [(news_id, fid) for fid in file_ids]
            batch_inserts.append(("INSERT INTO news_files_link (news_id, file_id) VALUES (%s, %s)", file_links))

        # Execute all batch inserts with error handling
        for query, data in batch_inserts:
            if data:
                try:
                    cursor.executemany(query, data)
                    logging.info(f"Successfully inserted {len(data)} records for: {query.split()[2]}")
                except Exception as e:
                    logging.error(f"Error inserting data with query {query}: {e}")
                    logging.error(f"Data sample: {data[:3] if len(data) > 3 else data}")
                    raise

        # First set all existing entities for this article to annotation_label = 0
        cursor.execute(
            "UPDATE autokmdb_persons SET annotation_label = 0 WHERE autokmdb_news_id = %s",
            (id,)
        )
        cursor.execute(
            "UPDATE autokmdb_institutions SET annotation_label = 0 WHERE autokmdb_news_id = %s",
            (id,)
        )
        cursor.execute(
            "UPDATE autokmdb_places SET annotation_label = 0 WHERE autokmdb_news_id = %s",
            (id,)
        )
        cursor.execute(
            "UPDATE autokmdb_others SET annotation_label = 0 WHERE autokmdb_news_id = %s",
            (id,)
        )
        cursor.execute(
            "UPDATE autokmdb_files SET annotation_label = 0 WHERE autokmdb_news_id = %s",
            (id,)
        )

        # Then update annotation labels to 1 for entities present in the request
        if person_updates:
            cursor.executemany(
                "UPDATE autokmdb_persons SET annotation_label = 1 WHERE id = %s",
                [(pid,) for pid in person_updates]
            )
            
        if institution_updates:
            cursor.executemany(
                "UPDATE autokmdb_institutions SET annotation_label = 1 WHERE id = %s",
                [(iid,) for iid in institution_updates]
            )
            
        if place_updates:
            cursor.executemany(
                "UPDATE autokmdb_places SET annotation_label = 1 WHERE id = %s",
                [(pid,) for pid in place_updates]
            )

        # Update others entities that are present in the request
        others_updates = []
        for other in others:
            if "id" in other and isinstance(other["id"], int):
                others_updates.append(other["id"])
        
        if others_updates:
            cursor.executemany(
                "UPDATE autokmdb_others SET annotation_label = 1 WHERE id = %s",
                [(oid,) for oid in others_updates]
            )
        
        # Update files entities that are present in the request
        files_updates = []
        for file_id in file_ids:
            if isinstance(file_id, int):
                files_updates.append(file_id)

        if files_updates:
            cursor.executemany(
                "UPDATE autokmdb_files SET annotation_label = 1 WHERE id = %s",
                [(fid,) for fid in files_updates]
            )

        # Handle tags last
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


def validate_user_credentials(connection: PooledMySQLConnection, username: str, password: str) -> Optional[int]:
    """
    Validate user credentials against the database.
    
    Args:
        connection: Database connection
        username: Username to validate
        password: Password to validate (will be MD5 hashed)
    
    Returns:
        User ID if valid, None if invalid
    """
    import hashlib
    
    # Hash the password using MD5
    password_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
    
    query = """SELECT user_id FROM users WHERE uname = %s AND upass = %s AND ustatus = 'Y'"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (username, password_hash))
        result = cursor.fetchone()
        return result["user_id"] if result else None


def create_user_session(connection: PooledMySQLConnection, user_id: int) -> str:
    """
    Create a new session for the user.
    
    Args:
        connection: Database connection
        user_id: ID of the user to create session for
    
    Returns:
        Session ID string
    """
    import secrets
    import time
    import string
    
    # Generate a secure random session ID using only alphanumeric characters
    alphabet = string.ascii_letters + string.digits
    session_id = ''.join(secrets.choice(alphabet) for _ in range(32))
    
    # Set session to expire in 8 hours
    current_time = int(time.time())
    expires_time = current_time + (8 * 60 * 60)  # 8 hours from now
    
    # Insert session into database
    query = """INSERT INTO users_sessions (session_id, registered, session_expires) 
               VALUES (%s, %s, %s)"""
    
    with connection.cursor() as cursor:
        cursor.execute(query, (session_id, user_id, expires_time))
    
    connection.commit()
    return session_id
