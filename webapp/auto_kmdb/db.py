from functools import cache
from mysql.connector.pooling import MySQLConnectionPool, PooledMySQLConnection
import os
from contextlib import closing
from datetime import datetime
from slugify import slugify
import logging

connection_pool = MySQLConnectionPool(
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
def get_all(
    connection: PooledMySQLConnection, table: str, id_column: str, name_column: str
) -> list[dir]:
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


def get_all_persons(connection: PooledMySQLConnection) -> list[dir]:
    """
    Queries person label id-name pairs.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' of a person and 'id' of its label.
    """
    return get_all(connection, "news_persons", "person_id", "name")


def get_all_institutions(connection: PooledMySQLConnection) -> list[dir]:
    """
    Queries institution label id-name pairs.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' of an institution and 'id' of its label.
    """
    return get_all(connection, "news_institutions", "institution_id", "name")


def get_all_places(connection: PooledMySQLConnection) -> list[dir]:
    """
    Queries place label id-name pairs.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' of a place and 'id' of its label.
    """
    return get_all(connection, "news_places", "place_id", "name_hu")


def get_all_others(connection: PooledMySQLConnection) -> list[dir]:
    """
    Queries other label id-name pairs.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' of the label and its 'id'.
    """
    return get_all(connection, "news_others", "other_id", "name_hu")


def get_all_files(connection: PooledMySQLConnection) -> list[dir]:
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


@cache
def get_all_freq(
    connection: PooledMySQLConnection, table: str, id_column: str, name_column: str
) -> list[dir]:
    """
    Queries label id-name pairs from given table and counts number of times the given label has
    been used on an article.

    Args:
        connection: db connection
        table: name of the table
        id_column: name of the column containing the ids
        name_column: name of the column containing the names

    Returns:
        List of dirs, each dir containing the 'name', 'id' and 'count' occurrances of a given label.
    """
    query = f'SELECT p.{id_column} AS id, p.{name_column} AS name, COUNT(npl.news_id) AS count FROM {table} p JOIN {table}_link npl ON p.{id_column} = npl.{id_column} WHERE status = "Y" GROUP BY p.{id_column};'
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return list(cursor.fetchall())


def get_all_persons_freq(connection: PooledMySQLConnection) -> list[dir]:
    """
    Queries person label id-name pairs and counts the number of times the given person label has
    been used on an article.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' and 'id' of a person label, as well as the
        'count' occurrances of the given label.
    """
    return get_all_freq(connection, "news_persons", "person_id", "name")


def get_all_institutions_freq(connection: PooledMySQLConnection) -> list[dir]:
    """
    Queries institution label id-name pairs and counts the number of times the given institution
    label has been used on an article.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' and 'id' of an institution label, as well as the
        'count' occurrances of the given label.
    """
    return get_all_freq(connection, "news_institutions", "institution_id", "name")


def get_all_places_freq(connection: PooledMySQLConnection) -> list[dir]:
    """
    Queries place label id-name pairs and counts the number of times the given place label has been
    used on an article.

    Args:
        connection: db connection

    Returns:
        List of dirs, each dir containing the 'name' and 'id' of a place label, as well as the
        'count' occurrances of the given label.
    """
    return get_all_freq(connection, "news_places", "place_id", "name_hu")


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


@cache
def get_all_newspapers(connection: PooledMySQLConnection):
    query = """SELECT n.newspaper_id AS id, n.name AS name, n.rss_url AS rss_url, COUNT(a.newspaper_id) AS article_count FROM news_newspapers n
    LEFT JOIN autokmdb_news a ON n.newspaper_id = a.newspaper_id WHERE n.status = "Y"
    GROUP BY n.newspaper_id, n.name, n.rss_url;"""
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


def init_news(
    connection: PooledMySQLConnection,
    source,
    source_url,
    clean_url,
    newspaper_name,
    newspaper_id,
    user_id,
):
    current_datetime = datetime.now()
    cre_time = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    with connection.cursor(dictionary=True) as cursor:
        query = """INSERT INTO autokmdb_news
                (source, source_url, clean_url, processing_step, cre_time, newspaper_name, newspaper_id, version_number, mod_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(
            query,
            (
                0 if source == "rss" else 1,
                source_url,
                clean_url,
                0,
                cre_time,
                newspaper_name,
                newspaper_id,
                VERSION_NUMBER,
                user_id,
            ),
        )
    connection.commit()


def check_url_exists(connection: PooledMySQLConnection, url):
    with connection.cursor() as cursor:
        query = "SELECT id FROM autokmdb_news WHERE clean_url = %s"
        cursor.execute(query, (url,))
        results = cursor.fetchall()

        return len(results) != 0


def add_auto_person(
    connection: PooledMySQLConnection,
    autokmdb_news_id,
    person_name,
    person_id,
    found_name,
    found_position,
    name,
    classification_score,
    classification_label,
):
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
    autokmdb_news_id,
    institution_name,
    institution_id,
    found_name,
    found_position,
    name,
    classification_score,
    classification_label,
):
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
    autokmdb_news_id,
    place_name,
    place_id,
    found_name,
    found_position,
    name,
    classification_score,
    classification_label,
):
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
    autokmdb_news_id,
    other_id,
    found_name,
    found_position,
    name,
    classification_score,
    classification_label,
):
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
    id,
    text,
    title,
    description,
    authors,
    date,
    is_paywalled,
):
    query = """UPDATE autokmdb_news SET text = %s, title = %s, description = %s, processing_step = 1, author = %s, article_date = %s, is_paywalled = %s
               WHERE id = %s;"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            query, (text, title, description, authors, date, is_paywalled, id)
        )
    connection.commit()


def skip_same_news(
    connection: PooledMySQLConnection,
    id,
    text,
    title,
    description,
    authors,
    date,
    is_paywalled,
):
    query = """UPDATE autokmdb_news SET skip_reason = 2, processing_step = 5, text = %s, title = %s, description = %s, processing_step = 1, author = %s, article_date = %s, is_paywalled = %s
               WHERE id = %s"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            query, (text, title, description, authors, date, is_paywalled, id)
        )
    connection.commit()


def skip_download_error(connection: PooledMySQLConnection, id):
    query = """UPDATE autokmdb_news SET skip_reason = 3, processing_step = 5
               WHERE id = %s"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (id,))
    connection.commit()


def save_classification_step(
    connection: PooledMySQLConnection,
    id,
    classification_label,
    classification_score,
    category,
):
    query = """UPDATE autokmdb_news SET classification_label = %s,
               classification_score = %s, processing_step = 2, category = %s WHERE id = %s"""
    with connection.cursor() as cursor:
        cursor.execute(
            query, (classification_label, classification_score, category, id)
        )
    connection.commit()


def get_retries_from(connection, date):
    query = """SELECT id, source_url AS url, source FROM autokmdb_news WHERE skip_reason = 3 AND cre_time >= %s AND processing_step = 5 ORDER BY source DESC, mod_time DESC"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (date,))
        return cursor.fetchall()


def get_step_queue(connection, step):
    fields = {
        0: "clean_url AS url, source",
        1: "title, description, text, source",
        2: "text",
        3: "text",
        4: "text",
    }
    query = f"""SELECT id, {fields[step]} FROM autokmdb_news
               WHERE processing_step = {step} ORDER BY source DESC, mod_time DESC LIMIT 1"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query)
        return cursor.fetchone()


def get_download_queue(connection: PooledMySQLConnection):
    return get_step_queue(connection, 0)


def get_classification_queue(connection: PooledMySQLConnection):
    return get_step_queue(connection, 1)


def get_ner_queue(connection: PooledMySQLConnection):
    return get_step_queue(connection, 2)


def get_keyword_queue(connection: PooledMySQLConnection):
    return get_step_queue(connection, 3)


def get_human_queue(connection: PooledMySQLConnection):
    return get_step_queue(connection, 4)


def paginate_query(query, page_size, page_number):
    offset = (page_number - 1) * page_size
    return query + f" LIMIT {page_size} OFFSET {offset}"


def get_article_counts(
    connection: PooledMySQLConnection,
    domains,
    q="",
    start="2000-01-01",
    end="2050-01-01",
):
    article_counts = {}
    for status in ["mixed", "positive", "negative", "processing", "all"]:
        if status == "mixed":
            query = """WHERE n.classification_label = 1 AND processing_step = 4 AND n.annotation_label IS NULL AND (n.skip_reason = 0 OR n.skip_reason is NULL)"""
        elif status == "positive":
            query = """WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 1"""
        elif status == "negative":
            query = """WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 0"""
        elif status == "processing":
            query = """WHERE processing_step < 4"""
        elif status == "all":
            query = """WHERE processing_step >= 0"""
        if domains and domains[0] != -1 and isinstance(domains, list):
            domain_list = ",".join([str(domain) for domain in domains])
            query += f" AND n.newspaper_id IN ({domain_list})"
        query += " AND (n.title LIKE %s OR n.description LIKE %s OR n.source_url LIKE %s OR n.newspaper_id LIKE %s)"
        query += ' AND DATE(n.cre_time) BETWEEN %s AND %s'
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT COUNT(id) FROM autokmdb_news n " + query,
                (q, q, q, q, start, end),
            )
            count = cursor.fetchone()["COUNT(id)"]
            article_counts[status] = count
    return article_counts


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


def get_article(connection: PooledMySQLConnection, id):
    query = """SELECT n.id AS id, news_id, clean_url AS url, description, title, source, newspaper_name, newspaper_id, n.classification_score AS classification_score, annotation_label, processing_step, skip_reason,
            n.text AS text, n.cre_time AS date, category, article_date, u.name AS mod_name FROM autokmdb_news n LEFT JOIN users u ON n.mod_id = u.user_id WHERE id = %s
        """
    with connection.cursor(dictionary=True) as cursor:
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





def get_articles(
    connection, page, status, domains, q="", start="2000-01-01", end="2050-01-01", reverse=False
):
    query = ""

    selection = """SELECT n.id AS id, clean_url AS url, description, title, source, newspaper_name, newspaper_id, n.classification_score AS classification_score, n.classification_label AS classification_label, annotation_label, processing_step, skip_reason, negative_reason,
            n.cre_time AS date, category, u.name AS mod_name
        FROM autokmdb_news n
        LEFT JOIN users u ON n.mod_id = u.user_id
        """
    group = (
        " GROUP BY id ORDER BY source DESC, n.mod_time "+('ASC' if reverse else 'DESC')
        if status != "positive"
        else " GROUP BY id ORDER BY n.mod_time "+('ASC' if reverse else 'DESC')
    )

    if status == "mixed":
        query = """WHERE n.classification_label = 1 AND processing_step = 4 AND n.annotation_label IS NULL AND (n.skip_reason = 0 OR n.skip_reason is NULL)"""
    elif status == "positive":
        query = """WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 1"""
    elif status == "negative":
        query = """WHERE n.classification_label = 1 AND processing_step = 5 AND n.annotation_label = 0"""
    elif status == "processing":
        query = """WHERE processing_step < 4"""
    elif status == "all":
        query = """WHERE processing_step >= 0"""
    else:
        print("Invalid status provided!")
        return
    if domains and domains[0] != -1 and isinstance(domains, list):
        domain_list = ",".join([str(domain) for domain in domains])
        query += f" AND n.newspaper_id IN ({domain_list})"

    query += " AND (n.title LIKE %s OR n.description LIKE %s OR n.source_url LIKE %s OR n.newspaper_id LIKE %s)"

    query += " AND DATE(n.cre_time) BETWEEN %s AND %s"

    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(
            "SELECT COUNT(id) FROM autokmdb_news n " + query, (q, q, q, q, start, end)
        )
        count = cursor.fetchone()["COUNT(id)"]
        cursor.execute(
            paginate_query(selection + query + group, 10, page),
            (q, q, q, q, start, end),
        )
        return count, cursor.fetchall()


def force_accept_article(connection: PooledMySQLConnection, id, user_id):
    query = """UPDATE autokmdb_news SET classification_label = 1, processing_step = 2, source = 1, mod_id = %s WHERE id = %s;"""
    with connection.cursor() as cursor:
        cursor.execute(query, (id, user_id))
    connection.commit()


def annote_negative(connection: PooledMySQLConnection, id, reason, user_id):
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
        news_id = cursor.fetchone()[0]
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


def create_person(connection, name, user_id):
    logging.info("adding new person: " + name)
    query = """INSERT INTO news_persons (status, name, cre_id, mod_id, import_id, cre_time, mod_time) VALUES (%s, %s, %s, %s, %s, %s, %s);"""
    query_seo = """INSERT INTO tags_seo_data (seo_name, tag_type, item_id) VALUES (%s, %s, %s);"""
    query_check_person = """SELECT person_id FROM news_persons WHERE name = %s;"""

    current_datetime = datetime.now()
    cre_time = int(current_datetime.timestamp())

    with connection.cursor() as cursor:
        cursor.execute(query_check_person, (name,))
        result = cursor.fetchone()
        if result:
            person_id = result[0]
            logging.info(f"Person already exists with ID: {person_id}")
            return person_id

        cursor.execute(query, ("Y", name, user_id, user_id, 0, cre_time, cre_time))
        db_id = cursor.lastrowid
        cursor.execute(query_seo, (slugify(name), "persons", db_id))
    connection.commit()
    return db_id


def create_institution(connection, name, user_id):
    logging.info("adding new institution: " + name)
    query = """INSERT INTO news_institutions (status, name, cre_id, mod_id, import_id, cre_time, mod_time) VALUES (%s, %s, %s, %s, %s, %s, %s);"""
    query_seo = """INSERT INTO tags_seo_data (seo_name, tag_type, item_id) VALUES (%s, %s, %s);"""
    query_check_institution = (
        """SELECT institution_id FROM news_institutions WHERE name = %s;"""
    )

    current_datetime = datetime.now()
    cre_time = int(current_datetime.timestamp())

    with connection.cursor() as cursor:
        cursor.execute(query_check_institution, (name,))
        result = cursor.fetchone()
        if result:
            institution_id = result[0]
            logging.info(f"Institution already exists with ID: {institution_id}")
            return institution_id

        cursor.execute(query, ("Y", name, user_id, user_id, 0, cre_time, cre_time))
        db_id = cursor.lastrowid
        cursor.execute(query_seo, (slugify(name), "institutions", db_id))
    connection.commit()
    return db_id


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
    user_id,
    is_active,
    category,
    others,
    file_ids,
    pub_date,
):
    query_0 = """SELECT news_id FROM autokmdb_news WHERE id = %s LIMIT 1"""
    query_1 = """UPDATE autokmdb_news SET annotation_label = 1, processing_step = 5, news_id = %s, title = %s, description = %s, text = %s, mod_id = %s WHERE id = %s;"""
    query_2 = """INSERT INTO news_news (source_url, source_url_string, cre_time, mod_time, pub_time, cre_id, mod_id, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"""
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
    query_cat_update = """UPDATE news_categories_link
SET 
    cid = %s, 
    head = %s
WHERE 
    news_id = %s;"""
    query_p = """INSERT INTO news_persons_link (news_id, person_id) VALUES (%s, %s)"""
    delete_p = """DELETE FROM news_persons_link WHERE news_id = %s"""
    query_auto_p = """UPDATE autokmdb_persons SET annotation_label = 1 WHERE id = %s;"""
    query_i = """INSERT INTO news_institutions_link (news_id, institution_id) VALUES (%s, %s)"""
    delete_i = """DELETE FROM news_institutions_link WHERE news_id = %s"""
    query_auto_i = (
        """UPDATE autokmdb_institutions SET annotation_label = 1 WHERE id = %s;"""
    )
    query_pl = """INSERT INTO news_places_link (news_id, place_id) VALUES (%s, %s)"""
    delete_pl = """DELETE FROM news_places_link WHERE news_id = %s"""
    query_auto_pl = """UPDATE autokmdb_places SET annotation_label = 1 WHERE id = %s;"""
    query_others = (
        """INSERT INTO news_others_link (news_id, other_id) VALUES (%s, %s)"""
    )
    delete_others = """DELETE FROM news_others_link WHERE news_id = %s;"""
    query_file = """INSERT INTO news_files_link (news_id, file_id) VALUES (%s, %s)"""
    delete_file = """DELETE FROM news_files_link WHERE news_id = %s;"""

    current_datetime = datetime.now()
    cre_time = int(current_datetime.timestamp())

    with connection.cursor() as cursor:
        category_dict = {0: 5, 1: 6, 2: 7, None: 5}
        is_update = False
        alias = slugify(title)
        seo_url_default = "hirek/magyar-hirek/" + alias

        cursor.execute(query_0, (id,))
        news_id = cursor.fetchone()[0]

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
                db_id = create_person(connection, person["name"], user_id)
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


def validate_session(connection: PooledMySQLConnection, session_id):
    if "NO_LOGIN" in os.environ:
        return True
    query = """SELECT * FROM users_sessions WHERE session_id = %s;"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (session_id,))
        session = cursor.fetchone()
    if session is None or session["registered"] == 0:
        return None
    return session["registered"]


def get_roles(connection: PooledMySQLConnection, session_id):
    query = """SELECT * FROM users_sessions WHERE session_id = %s;"""
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query, (session_id,))
    session = cursor.fetchone()
    if session is None or session["registered"] == 0:
        return []

    user_id = session["registered"]

    query_u = """SELECT * FROM users_modul_rights WHERE user_id = %s;"""

    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(query_u, (user_id,))

    roles = [
        {
            "modul_name": r["modul_name"],
            "action_name": r["action_name"],
            "action_right": r["action_right"],
        }
        for r in cursor.fetchall()
    ]

    return roles
