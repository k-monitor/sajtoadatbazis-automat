from functools import cache
from typing import Literal, Any, Optional
from mysql.connector.pooling import MySQLConnectionPool
import os
from slugify import slugify
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from cachetools import cached, LRUCache, TTLCache
from sqlalchemy import create_engine, text, bindparam, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool
import re
import time
import json
from urllib.parse import urlparse
import nh3
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt
from auto_kmdb.utils.similar_entities import SimilarEntityIndex

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
    # Force buffered cursors so every result set is fully read on execute.
    # This eliminates the "Unread result found" class of errors that arise
    # when a lazy/unbuffered result is iterated while new queries run on the
    # same connection, which otherwise leaves the pooled connection broken and
    # poisons unrelated callers (e.g. the background processors).
    buffered=True,
)

engine: Engine = create_engine(
    "mysql+mysqlconnector://",
    creator=lambda: connection_pool.get_connection(),
    poolclass=NullPool,
)

slow_query_logger = logging.getLogger("autokmdb.slow_query")
SLOW_QUERY_THRESHOLD_S = float(os.environ.get("SLOW_QUERY_THRESHOLD_S", "0.5"))


@event.listens_for(engine, "before_cursor_execute")
def _record_query_start(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.monotonic()


@event.listens_for(engine, "after_cursor_execute")
def _log_slow_query(conn, cursor, statement, parameters, context, executemany):
    elapsed = time.monotonic() - context._query_start_time
    if elapsed >= SLOW_QUERY_THRESHOLD_S:
        slow_query_logger.warning(
            "slow_query elapsed=%.3fs rows=%s sql=%s params=%s",
            elapsed,
            cursor.rowcount,
            " ".join(statement.split()),
            parameters,
        )


def _fetch_all_dicts(query: str, params: Optional[dict] = None) -> list[dict]:
    """Execute a SELECT and return rows as a list of dicts."""
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row) for row in result.mappings()]


def _fetch_one_dict(query: str, params: Optional[dict] = None) -> Optional[dict]:
    """Execute a SELECT and return the first row as a dict, or None."""
    with engine.connect() as conn:
        row = conn.execute(text(query), params or {}).mappings().first()
        return dict(row) if row else None


def _fetch_scalar(query: str, params: Optional[dict] = None) -> Any:
    """Execute a SELECT and return the first column of the first row, or None."""
    with engine.connect() as conn:
        return conn.execute(text(query), params or {}).scalar()


def _execute(query: str, params: Optional[dict] = None) -> Optional[int]:
    """Execute an INSERT/UPDATE/DELETE in a transaction and return lastrowid."""
    with engine.begin() as conn:
        result = conn.execute(text(query), params or {})
        return result.lastrowid

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
    return _fetch_all_dicts(query)


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
    rows = _fetch_all_dicts(query)
    papers = [
        {
            "id": r["id"],
            "name": r["name"],
            "has_rss": bool(r["rss_url"]),
            "article_count": r["article_count"],
        }
        for r in rows
    ]
    papers.sort(key=lambda r: r["article_count"], reverse=True)
    return papers


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
    query = f'SELECT p.{id_column} AS id, p.{name_column} AS name, COUNT(npl.news_id) AS count FROM {table} p LEFT JOIN {table}_link npl ON p.{id_column} = npl.{id_column} WHERE p.status = "Y" GROUP BY p.{id_column};'
    return _fetch_all_dicts(query)


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


@cached(cache=TTLCache(maxsize=1, ttl=1800))
def get_similar_institutions_index() -> SimilarEntityIndex:
    """
    Index of all institutions for finding the existing ones that are written differently than a
    new name. Institutions created on the UI are added to it right away.
    """
    counts = {i["id"]: i["count"] for i in get_all_institutions_freq()}
    return SimilarEntityIndex(
        {"id": i["id"], "name": i["name"], "count": counts.get(i["id"], 0)}
        for i in get_all_institutions()
    )


def find_similar_institutions(name: str, limit: int = 3, min_score: float = 0.75) -> list[dict]:
    """
    Finds existing institutions that are probably the same as the given name, e.g.
    'Magyar Fejlesztési Bank (MFB)' for 'MFB Zrt.'. These are only suggestions to be confirmed by
    the user.

    Returns:
        List of dicts containing the 'id', 'name', 'count' and similarity 'score' of institutions.
    """
    return get_similar_institutions_index().find(name, limit=limit, min_score=min_score)


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


def get_all_files_freq() -> list[dict]:
    """
    Queries file id-name pairs and counts the number of times the given file has been used on an
    article.

    Returns:
        List of dicts, each dict containing the 'name' and 'id' of a file, as well as the 'count'
        occurrances of the given file.
    """
    return get_all_freq("news_files", "file_id", "name_hu")


def get_places_alias() -> list[dict]:
    query = """
    SELECT
        np.name_hu AS place_name,
        ap.alias_name
    FROM
        news_places np
        JOIN autokmdb_alias_place ap ON np.place_id = ap.place_id;
    """
    return _fetch_all_dicts(query)


def process_and_accept_article(id: int, user_id: int) -> None:
    _execute(
        """UPDATE autokmdb_news SET processing_step = 2, skip_reason = NULL,
           mod_id = :user_id, source = 1, classification_label = 1 WHERE id = :id""",
        {"user_id": user_id, "id": id},
    )


def init_news(
    source: str,
    source_url: str,
    clean_url: str,
    newspaper_name: str,
    newspaper_id: int,
    user_id: Optional[int],
    pub_time: Optional[str],
) -> None:
    source_value = 0
    if source == "manual":
        source_value = 1
    elif source == "api":
        source_value = 2
    cre_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _execute(
        """INSERT INTO autokmdb_news
           (source, source_url, clean_url, processing_step, cre_time, article_date,
            newspaper_name, newspaper_id, version_number, mod_id)
           VALUES (:source, :source_url, :clean_url, 0, :cre_time, :pub_time,
                   :newspaper_name, :newspaper_id, :version, :user_id)""",
        {
            "source": source_value,
            "source_url": source_url,
            "clean_url": clean_url,
            "cre_time": cre_time,
            "pub_time": pub_time,
            "newspaper_name": newspaper_name,
            "newspaper_id": newspaper_id,
            "version": VERSION_NUMBER,
            "user_id": user_id,
        },
    )


def url_exists_in_kmdb(url: str) -> bool:
    return _fetch_scalar(
        "SELECT 1 FROM news_news WHERE source_url LIKE :pat LIMIT 1",
        {"pat": f"%{url}%"},
    ) is not None


def check_url_exists(url: str) -> bool:
    return _fetch_scalar(
        "SELECT 1 FROM autokmdb_news WHERE clean_url = :url LIMIT 1",
        {"url": url},
    ) is not None


def _add_auto_entity(
    table: str,
    name_col: str,
    id_col: str,
    autokmdb_news_id: int,
    entity_name: str,
    entity_id: int,
    found_name: str,
    found_position: int,
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    query = f"""INSERT INTO {table}
            (autokmdb_news_id, {name_col}, {id_col}, found_name, found_position, name,
             classification_score, classification_label, version_number)
            VALUES (:news_id, :entity_name, :entity_id, :found_name, :found_position,
                    :name, :score, :label, :version)"""
    _execute(query, {
        "news_id": autokmdb_news_id,
        "entity_name": entity_name,
        "entity_id": entity_id,
        "found_name": found_name,
        "found_position": found_position,
        "name": name,
        "score": classification_score,
        "label": classification_label,
        "version": VERSION_NUMBER,
    })


def add_auto_person(
    autokmdb_news_id: int,
    person_name: str,
    person_id: int,
    found_name: str,
    found_position: int,
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    _add_auto_entity(
        "autokmdb_persons", "person_name", "person_id",
        autokmdb_news_id, person_name, person_id, found_name, found_position,
        name, classification_score, classification_label,
    )


def add_auto_institution(
    autokmdb_news_id: int,
    institution_name: str,
    institution_id: int,
    found_name: str,
    found_position: int,
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    _add_auto_entity(
        "autokmdb_institutions", "institution_name", "institution_id",
        autokmdb_news_id, institution_name, institution_id, found_name, found_position,
        name, classification_score, classification_label,
    )


def add_auto_place(
    autokmdb_news_id: int,
    place_name: str,
    place_id: int,
    found_name: str,
    found_position: int,
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    _add_auto_entity(
        "autokmdb_places", "place_name", "place_id",
        autokmdb_news_id, place_name, place_id, found_name, found_position,
        name, classification_score, classification_label,
    )


def add_auto_other(
    autokmdb_news_id: int,
    other_id: int,
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    _execute(
        """INSERT INTO autokmdb_others
           (autokmdb_news_id, other_id, name, classification_score, classification_label, version_number)
           VALUES (:news_id, :other_id, :name, :score, :label, :version)""",
        {
            "news_id": autokmdb_news_id,
            "other_id": other_id,
            "name": name,
            "score": classification_score,
            "label": classification_label,
            "version": VERSION_NUMBER,
        },
    )


def add_auto_files(
    autokmdb_news_id: int,
    files_id: int,
    name: str,
    classification_score: float,
    classification_label: int,
) -> None:
    _execute(
        """INSERT INTO autokmdb_files
           (autokmdb_news_id, files_id, name, classification_score, classification_label, version_number)
           VALUES (:news_id, :files_id, :name, :score, :label, :version)""",
        {
            "news_id": autokmdb_news_id,
            "files_id": files_id,
            "name": name,
            "score": classification_score,
            "label": classification_label,
            "version": VERSION_NUMBER,
        },
    )


def save_download_step(
    id: int,
    text: str,
    title: str,
    description: str,
    authors: str,
    date: Optional[str],
    is_paywalled: int,
) -> None:
    _execute(
        """UPDATE autokmdb_news
           SET text = :text,
               title = :title,
               description = :description,
               processing_step = 1,
               skip_reason = NULL,
               author = :authors,
               article_date = COALESCE(:date, article_date),
               is_paywalled = :is_paywalled
           WHERE id = :id""",
        {
            "text": text, "title": title, "description": description,
            "authors": authors, "date": date, "is_paywalled": is_paywalled, "id": id,
        },
    )


def skip_same_news(
    id: int,
    text: str,
    title: str,
    description: str,
    authors: str,
    date: Optional[str],
    is_paywalled: int,
) -> None:
    _execute(
        """UPDATE autokmdb_news SET skip_reason = 2, processing_step = 5, text = :text,
           title = :title, description = :description, processing_step = 1, author = :authors,
           article_date = COALESCE(:date, article_date), is_paywalled = :is_paywalled
           WHERE id = :id""",
        {
            "text": text, "title": title, "description": description,
            "authors": authors, "date": date, "is_paywalled": is_paywalled, "id": id,
        },
    )


def skip_download_error(id: int) -> None:
    _execute(
        "UPDATE autokmdb_news SET skip_reason = 3, processing_step = 5 WHERE id = :id",
        {"id": id},
    )


def skip_processing_error(id: int) -> None:
    _execute(
        "UPDATE autokmdb_news SET skip_reason = 4, processing_step = 5 WHERE id = :id",
        {"id": id},
    )


def save_classification_step(
    id: int,
    classification_label: int,
    classification_score: float,
    category: int,
) -> None:
    new_step = 5 if classification_label == 0 else 2
    _execute(
        """UPDATE autokmdb_news SET classification_label = :label,
           classification_score = :score, processing_step = :step, category = :category
           WHERE id = :id""",
        {
            "label": classification_label, "score": classification_score,
            "step": new_step, "category": category, "id": id,
        },
    )


def get_retries_from(date: str) -> list[dict]:
    query = """SELECT id, source_url AS url, source, newspaper_id FROM autokmdb_news WHERE skip_reason = 3 AND cre_time >= :date AND processing_step = 5 ORDER BY source DESC, mod_time DESC"""
    return _fetch_all_dicts(query, {"date": date})


def get_step_queue(step: int) -> list[dict[str, Any]]:
    process_old = int(os.environ.get("PROCESS_OLD", "0")) == 1
    process_old_user_id = os.environ.get("PROCESS_OLD_USER_ID", None)
    fields: dict[int, str] = {
        0: "clean_url AS url, source, newspaper_id",
        1: "title, description, text, source, newspaper_name, clean_url",
        2: "text",
        3: "text",
        4: "text",
    }

    query = f"SELECT id, {fields[step]} FROM autokmdb_news WHERE processing_step = :step"
    params: dict[str, Any] = {"step": step}

    if process_old_user_id is not None:
        params["user_id"] = int(process_old_user_id)
        if process_old:
            query += " AND mod_id = :user_id"
        else:
            query += " AND (mod_id != :user_id OR mod_id IS NULL)"

    query += " ORDER BY source DESC, article_date ASC, mod_time ASC LIMIT 50"
    return _fetch_all_dicts(query, params)


def get_download_queue() -> list[dict[str, Any]]:
    return get_step_queue(0)


def get_classification_queue() -> list[dict[str, Any]]:
    return get_step_queue(1)


def get_ner_queue() -> list[dict[str, Any]]:
    return get_step_queue(2)


def get_keyword_queue() -> list[dict[str, Any]]:
    return get_step_queue(3)


def get_human_queue() -> list[dict[str, Any]]:
    return get_step_queue(4)


@cached(cache=TTLCache(maxsize=64, ttl=3600))
def get_articles_by_day(
    newspaper_id: Optional[int] = None,
    start: str = "2000-01-01",
    end: str = "2050-01-01",
) -> list[dict]:
    conditions = ["article_date BETWEEN :start AND :end"]
    params: dict[str, Any] = {
        "start": start + " 00:00:00",
        "end": end + " 23:59:59",
    }
    if newspaper_id:
        conditions.append("newspaper_id = :newspaper_id")
        params["newspaper_id"] = newspaper_id

    where_clause = " AND ".join(conditions)
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
        WHERE {where_clause}
        GROUP BY DATE(article_date)
        ORDER BY date
    """
    rows = _fetch_all_dicts(query, params)

    final_results = []
    for row in rows:
        count_negative = (
            row["count_negative_0"] + row["count_negative_1"]
            + row["count_negative_2"] + row["count_negative_3"]
            + row["count_negative_100"]
        )
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
            "count_todo": row["count_todo"],
        })
    return final_results

# Add these indexes to your database for optimal performance:
# CREATE INDEX idx_autokmdb_news_article_date ON autokmdb_news (article_date);
# CREATE INDEX idx_autokmdb_news_processing_annotation ON autokmdb_news (processing_step, annotation_label, negative_reason);
# CREATE INDEX idx_autokmdb_news_classification_step ON autokmdb_news (classification_label, processing_step, annotation_label, skip_reason);
# CREATE INDEX idx_autokmdb_news_newspaper_date ON autokmdb_news (newspaper_id, article_date);
# CREATE INDEX idx_autokmdb_news_compound ON autokmdb_news (article_date, newspaper_id, processing_step, annotation_label, classification_label);


def find_group_by_autokmdb_id(autokmdb_id):
    return _fetch_scalar(
        "SELECT group_id FROM autokmdb_news_groups WHERE autokmdb_news_id = :id",
        {"id": autokmdb_id},
    )


def add_article_group(autokmdb_id) -> int:
    rowid = _execute(
        """INSERT INTO autokmdb_news_groups (group_id, autokmdb_news_id, is_main)
           VALUES (
               (SELECT new_group_id FROM
                   (SELECT COALESCE(MAX(group_id) + 1, 1) AS new_group_id FROM autokmdb_news_groups) AS temp),
               :autokmdb_id,
               TRUE
           )""",
        {"autokmdb_id": autokmdb_id},
    )
    group_id = find_group_by_autokmdb_id(autokmdb_id)
    _execute(
        "UPDATE autokmdb_news SET group_id = :group_id WHERE id = :id",
        {"group_id": group_id, "id": autokmdb_id},
    )
    return rowid


def add_article_to_group(autokmdb_id, group_id):
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO autokmdb_news_groups (group_id, autokmdb_news_id, is_main)
                    VALUES (:group_id, :autokmdb_id, FALSE)"""),
            {"group_id": group_id, "autokmdb_id": autokmdb_id},
        )
        conn.execute(
            text("UPDATE autokmdb_news SET group_id = :group_id WHERE id = :id"),
            {"group_id": group_id, "id": autokmdb_id},
        )


def pick_out_article(autokmdb_id, user_id):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE autokmdb_news SET source = 1, group_id = NULL, mod_id = :user_id WHERE id = :id"),
            {"user_id": user_id, "id": autokmdb_id},
        )
        conn.execute(
            text("DELETE FROM autokmdb_news_groups WHERE autokmdb_news_id = :id"),
            {"id": autokmdb_id},
        )


_ARTICLE_BASE_COLUMNS = """
    n.id,
    n.group_id,
    n.news_id,
    n.source_url,
    n.clean_url AS url,
    n.description,
    n.title,
    n.source,
    n.newspaper_name,
    n.newspaper_id,
    n.classification_score,
    n.classification_label,
    n.annotation_label,
    n.processing_step,
    n.skip_reason,
    n.text,
    CONVERT_TZ(n.article_date, @@session.time_zone, '+00:00') AS date,
    n.category,
    CONVERT_TZ(n.article_date, @@session.time_zone, '+00:00') AS article_date,
    u.name AS mod_name,
    n.is_paywalled
"""


def _attach_article_entities(conn, article: dict) -> None:
    aid = article["id"]
    article["persons"] = map_entities(_fetch_article_persons(conn, aid))
    article["institutions"] = map_entities(_fetch_article_institutions(conn, aid))
    article["places"] = map_entities(_fetch_article_places(conn, aid))
    article["tags"] = map_entities(get_article_others(conn, aid))
    article["files"] = map_entities(get_article_files(conn, aid))


def find_article_by_url_with_group(source_url: str) -> Optional[dict[str, Any]]:
    """
    Find an article by its source_url and return it along with all articles in its group.

    Returns:
        Dict with 'main_article' and 'grouped_articles' list, or None if not found
    """
    find_query = f"""
        SELECT {_ARTICLE_BASE_COLUMNS}
        FROM autokmdb_news n
        LEFT JOIN users u ON n.mod_id = u.user_id
        WHERE n.source_url IN (:source_url, :source_url_slash)
        LIMIT 1
    """
    stripped_url = source_url.rstrip('/')
    group_query = f"""
        SELECT {_ARTICLE_BASE_COLUMNS}, ang.is_main
        FROM autokmdb_news n
        LEFT JOIN users u ON n.mod_id = u.user_id
        LEFT JOIN autokmdb_news_groups ang ON n.id = ang.autokmdb_news_id
        WHERE n.group_id = :group_id AND n.id != :main_id
        ORDER BY ang.is_main DESC, n.article_date DESC
    """

    with engine.connect() as conn:
        main_row = conn.execute(
            text(find_query),
            {"source_url": stripped_url, "source_url_slash": stripped_url + "/"},
        ).mappings().first()
        if not main_row:
            return None

        main_article = dict(main_row)
        group_id = main_article.get("group_id")
        _attach_article_entities(conn, main_article)

        grouped_articles: list[dict] = []
        if group_id is not None:
            # Fully materialize the result before running the per-row entity
            # queries below. Iterating a lazy (unbuffered) result while issuing
            # new queries on the same connection raises mysql.connector's
            # "Unread result found" and leaves the pooled connection in a broken
            # state, which then poisons unrelated callers (e.g. the processors).
            rows = list(conn.execute(
                text(group_query),
                {"group_id": group_id, "main_id": main_article["id"]},
            ).mappings())
            for row in rows:
                article = dict(row)
                _attach_article_entities(conn, article)
                grouped_articles.append(article)

        return {
            "main_article": main_article,
            "grouped_articles": grouped_articles,
            "group_id": group_id,
        }


def _fetch_article_persons(conn, article_id: int) -> list[dict]:
    """Helper function to fetch person entities for an article"""
    query = """
        SELECT
            id,
            name,
            person_id AS db_id,
            person_name AS db_name,
            classification_score,
            classification_label,
            annotation_label,
            found_name,
            found_position
        FROM autokmdb_persons
        WHERE autokmdb_news_id = :id
        ORDER BY id
    """
    return [dict(r) for r in conn.execute(text(query), {"id": article_id}).mappings()]


def _fetch_article_institutions(conn, article_id: int) -> list[dict]:
    """Helper function to fetch institution entities for an article"""
    query = """
        SELECT
            id,
            name,
            institution_id AS db_id,
            institution_name AS db_name,
            classification_score,
            classification_label,
            annotation_label,
            found_name,
            found_position
        FROM autokmdb_institutions
        WHERE autokmdb_news_id = :id
        ORDER BY id
    """
    return [dict(r) for r in conn.execute(text(query), {"id": article_id}).mappings()]


def _fetch_article_places(conn, article_id: int) -> list[dict]:
    """Helper function to fetch place entities for an article"""
    query = """
        SELECT
            id,
            name,
            place_id AS db_id,
            place_name AS db_name,
            classification_score,
            classification_label,
            annotation_label,
            found_name,
            found_position
        FROM autokmdb_places
        WHERE autokmdb_news_id = :id
        ORDER BY id
    """
    return [dict(r) for r in conn.execute(text(query), {"id": article_id}).mappings()]


def get_article_others(conn, id) -> list[dict]:
    query = """SELECT name, id, other_id AS db_id, name AS db_name, classification_score, classification_label, annotation_label FROM autokmdb_others WHERE autokmdb_news_id = :id"""
    return [dict(r) for r in conn.execute(text(query), {"id": id}).mappings()]


def _bulk_fetch_recommended_tags(
    conn, article_ids: list[int]
) -> dict[int, dict[str, list[dict]]]:
    """Bulk-fetch a slim list of recommended/confirmed entity tags per article.

    Returned per-article dict has keys 'persons' and 'institutions'; each is a
    deduped (by db_id or name) list of {name, db_id}. An entity is included
    when it was either confirmed by annotation (annotation_label=1) or, if
    not yet annotated, recommended by the classifier (classification_label=1).
    """
    result: dict[int, dict[str, list[dict]]] = {
        aid: {"persons": [], "institutions": []} for aid in article_ids
    }
    if not article_ids:
        return result
    ids_list = ",".join(str(int(a)) for a in article_ids)
    where = (
        f"autokmdb_news_id IN ({ids_list}) AND "
        "(annotation_label = 1 OR (annotation_label IS NULL AND classification_label = 1))"
    )
    for kind, table, fk, fk_name in (
        ("persons", "autokmdb_persons", "person_id", "person_name"),
        ("institutions", "autokmdb_institutions", "institution_id", "institution_name"),
    ):
        seen: dict[int, set] = {aid: set() for aid in article_ids}
        query = f"""
            SELECT autokmdb_news_id AS aid, name, {fk} AS db_id, {fk_name} AS db_name
            FROM {table}
            WHERE {where}
            ORDER BY autokmdb_news_id, id
        """
        for row in conn.execute(text(query)).mappings():
            aid = row["aid"]
            key = row["db_id"] if row["db_id"] is not None else row["name"]
            if key in seen[aid]:
                continue
            seen[aid].add(key)
            display_name = row["db_name"] if row["db_id"] is not None else row["name"]
            result[aid][kind].append(
                {"name": display_name, "db_id": row["db_id"]}
            )
    return result


def get_article_files(conn, id) -> list[dict]:
    query = """SELECT name, id, files_id AS db_id, name AS db_name, classification_score, classification_label, annotation_label FROM autokmdb_files WHERE autokmdb_news_id = :id"""
    return [dict(r) for r in conn.execute(text(query), {"id": id}).mappings()]


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


def get_article(id: int) -> dict[str, Any]:
    """
    Fetch a single article and its entities without causing a cartesian product explosion.
    """
    article_query = """
        SELECT
            n.id AS id,
            n.news_id,
            n.clean_url AS url,
            n.description,
            n.title,
            n.source,
            n.newspaper_name,
            n.newspaper_id,
            n.classification_score,
            n.classification_label,
            n.annotation_label,
            n.processing_step,
            n.skip_reason,
            n.text,
            CONVERT_TZ(n.article_date, @@session.time_zone, '+00:00') AS date,
            n.category,
            CONVERT_TZ(n.article_date, @@session.time_zone, '+00:00') AS article_date,
            u.name AS mod_name,
            n.is_paywalled
        FROM autokmdb_news n
        LEFT JOIN users u ON n.mod_id = u.user_id
        WHERE n.id = :id
    """
    kmdb_query = """
        SELECT 'person' AS entity_type, pl.person_id AS entity_id
        FROM news_persons_link pl WHERE pl.news_id = :news_id
        UNION ALL
        SELECT 'institution' AS entity_type, il.institution_id AS entity_id
        FROM news_institutions_link il WHERE il.news_id = :news_id
        UNION ALL
        SELECT 'place' AS entity_type, pll.place_id AS entity_id
        FROM news_places_link pll WHERE pll.news_id = :news_id
        UNION ALL
        SELECT 'other' AS entity_type, ol.other_id AS entity_id
        FROM news_others_link ol WHERE ol.news_id = :news_id
    """

    with engine.connect() as conn:
        row = conn.execute(text(article_query), {"id": id}).mappings().first()
        if not row:
            return {}
        article = dict(row)

        persons = _fetch_article_persons(conn, id)
        institutions = _fetch_article_institutions(conn, id)
        places = _fetch_article_places(conn, id)
        others = get_article_others(conn, id)
        files = get_article_files(conn, id)

        news_id = article.get("news_id")
        if news_id:
            for entity in conn.execute(text(kmdb_query), {"news_id": news_id}).mappings():
                etype = entity["entity_type"]
                eid = entity["entity_id"]
                if etype == "person" and eid in all_persons_by_id:
                    persons.append({
                        "annotation_label": 1,
                        "db_id": eid,
                        "name": all_persons_by_id[eid],
                        "db_name": all_persons_by_id[eid],
                    })
                elif etype == "institution" and eid in all_institutions_by_id:
                    institutions.append({
                        "annotation_label": 1,
                        "db_id": eid,
                        "name": all_institutions_by_id[eid],
                        "db_name": all_institutions_by_id[eid],
                    })
                elif etype == "place" and eid in all_places_by_id:
                    places.append({
                        "annotation_label": 1,
                        "db_id": eid,
                        "name": all_places_by_id[eid],
                        "db_name": all_places_by_id[eid],
                    })
                elif etype == "other" and eid in all_others_by_id:
                    others.append({
                        "annotation_label": 1,
                        "db_id": eid,
                        "name": all_others_by_id[eid],
                        "db_name": all_others_by_id[eid],
                    })

    article["mapped_persons"] = map_entities(persons)
    article["mapped_institutions"] = map_entities(institutions)
    article["mapped_places"] = map_entities(places)
    article["others"] = others
    article["files"] = files
    _attach_similar_institutions(article["mapped_institutions"])

    return article


def _attach_similar_institutions(mapped_institutions: list[dict]) -> None:
    """
    Adds the 'similar' existing institutions to the institutions not linked to the db, so the user
    can pick one of them instead of creating a duplicate.
    """
    linked_ids = {e["db_id"] for e in mapped_institutions if e.get("db_id")}
    for entity in mapped_institutions:
        if entity.get("db_id") or not entity.get("name"):
            continue
        similar = find_similar_institutions(entity["name"], limit=2)
        # most probably a variant of an institution already linked to the article, e.g. 'MFB Zrt.'
        # next to 'Magyar Fejlesztési Bank (MFB)', no need to suggest anything else
        if similar and similar[0]["id"] in linked_ids:
            continue
        entity["similar"] = [s for s in similar if s["id"] not in linked_ids]


def group_articles(articles):
    """
    This function is no longer needed as the get_articles function now handles grouping internally.
    Kept for backward compatibility but just returns articles as-is.
    """
    return articles


def _score_bucket_range(score_bucket: int) -> Optional[tuple[float, float]]:
    buckets = {
        0: (0.9, 1.0001),
        1: (0.75, 0.9),
        2: (0.5, 0.75),
        3: (0.0, 0.5),
    }
    return buckets.get(score_bucket)


def get_article_counts(
    domains: list[int],
    search_query="",
    start="2000-01-01",
    end="2050-01-01",
    skip_reason: int = -1,
    is_url_search: bool = False,
    cleaned_url: str = "",
    score_bucket: int = -1,
) -> dict[str, int]:
    params: dict[str, Any] = {
        "start": start + " 00:00:00",
        "end": end + " 23:59:59",
    }

    domain_condition = ""
    if domains and domains[0] != -1 and isinstance(domains, list):
        domain_list = ",".join([str(domain) for domain in domains])
        domain_condition = f" AND n.newspaper_id IN ({domain_list})"

    search_condition = ""
    if is_url_search and cleaned_url:
        search_condition = " AND n.source_url = :cleaned_url"
        params["cleaned_url"] = cleaned_url
    elif search_query != "%%":
        search_condition = " AND (n.title LIKE :q OR n.description LIKE :q OR n.source_url LIKE :q)"
        params["q"] = search_query

    skip_condition = ""
    if skip_reason != -1:
        skip_condition = " AND n.skip_reason = " + str(int(skip_reason))

    score_condition = ""
    score_range = _score_bucket_range(score_bucket)
    if score_range is not None:
        score_condition = " AND n.classification_score >= :score_min AND n.classification_score < :score_max"
        params["score_min"] = score_range[0]
        params["score_max"] = score_range[1]

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
        {search_condition}
        {score_condition}
        AND n.article_date BETWEEN :start AND :end
    """

    result = _fetch_one_dict(query, params)
    if not result:
        return {}
    return {
        "mixed": result["mixed"],
        "positive": result["positive"],
        "negative": result["negative"],
        "processing": result["processing"],
        "all": result["all_status"],
    }


def _build_search_condition(
    search_query: str, use_fulltext: bool = False
) -> tuple[str, dict, bool]:
    """
    Build an optimized search condition.
    Returns (condition_sql, params_dict, is_fulltext)

    Note: FULLTEXT is disabled by default as MySQL 5.5 has limited FULLTEXT support on InnoDB.
    If you have upgraded to MySQL 5.6+ with FULLTEXT index on (title, description),
    set use_fulltext=True.
    """
    search_term = search_query.strip('%')
    if not search_term:
        return "", {}, False

    if use_fulltext and len(search_term) >= 3:
        return (
            "MATCH(n.title, n.description) AGAINST(:ft_term IN BOOLEAN MODE)",
            {"ft_term": f"+{search_term}*"},
            True,
        )
    return (
        "(n.title LIKE :q OR n.description LIKE :q OR n.source_url LIKE :q)",
        {"q": search_query},
        False,
    )


def get_articles(
    page: int,
    status: str,
    domains: list[int],
    search_query="",
    start="2000-01-01",
    end="2050-01-01",
    reverse=False,
    skip_reason: int = -1,
    is_url_search: bool = False,
    cleaned_url: str = "",
    score_bucket: int = -1,
) -> Optional[tuple[int, list[dict[str, Any]]]]:
    conditions: list[str] = []
    params: dict[str, Any] = {
        "start": start + " 00:00:00",
        "end": end + " 23:59:59",
    }
    has_text_search = False

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
    if is_url_search and cleaned_url:
        conditions.append("n.source_url = :cleaned_url")
        params["cleaned_url"] = cleaned_url
    elif search_query != "%%" and search_query:
        has_text_search = True
        search_condition, search_params, _is_fulltext = _build_search_condition(search_query)
        if search_condition:
            conditions.append(search_condition)
            params.update(search_params)

    # Date condition
    conditions.append("n.article_date BETWEEN :start AND :end")

    # Skip reason condition
    if skip_reason != -1:
        conditions.append("n.skip_reason = :skip_reason")
        params["skip_reason"] = skip_reason

    # Score bucket condition
    score_range = _score_bucket_range(score_bucket)
    if score_range is not None:
        conditions.append("n.classification_score >= :score_min AND n.classification_score < :score_max")
        params["score_min"] = score_range[0]
        params["score_max"] = score_range[1]

    where_clause = " AND ".join(conditions)
    where_main = where_clause.replace("n.", "main.")

    # Sort configuration
    sort_order = "ASC" if reverse else "DESC"
    if status != "positive":
        # source DESC is fixed; article_date follows sort_order
        order_by_full = f"main.source DESC, main.article_date {sort_order}"
        order_by_agg = f"MAX(main.source) DESC, MAX(main.article_date) {sort_order}"
    else:
        order_by_full = f"main.article_date {sort_order}"
        order_by_agg = f"MAX(main.article_date) {sort_order}"
    offset = (page - 1) * 10

    main_article_cols = """
        main.id, main.clean_url AS url, main.description, main.title, main.source,
        main.newspaper_name, main.newspaper_id, main.classification_score,
        main.classification_label, main.annotation_label, main.processing_step,
        main.skip_reason, main.negative_reason,
        CONVERT_TZ(main.article_date, @@session.time_zone, '+00:00') AS date,
        main.category, u.name AS mod_name, main.group_id
    """

    with engine.connect() as conn:
        # One scan: dedup by group, sort by aggregated sort columns, page in
        # SQL. Only 10 IDs ever cross the wire from this query — the heavy
        # heap reads happen for those 10 rows in the follow-up fetch.
        # COALESCE(group_id, -id) gives ungrouped rows their own singleton
        # group; MAX() of the sort columns picks any value (within a group
        # they are typically equal), and serves as the sort key.
        # Pick the is_main=TRUE article from autokmdb_news_groups as the
        # group's representative, regardless of whether it matches the filter.
        # The WHERE filter only decides whether the group APPEARS (any
        # article in the group matching qualifies it). Falls back to MIN(id)
        # for ungrouped articles or when no is_main row exists.
        page_query = f"""
            SELECT COALESCE(MAX(ang.autokmdb_news_id), MIN(main.id)) AS id
            FROM autokmdb_news main
            LEFT JOIN autokmdb_news_groups ang
              ON ang.group_id = main.group_id AND ang.is_main = TRUE
            WHERE {where_main}
            GROUP BY COALESCE(main.group_id, -main.id)
            ORDER BY {order_by_agg}
            LIMIT 10 OFFSET {offset}
        """
        page_ids = [
            r["id"] for r in conn.execute(text(page_query), params).mappings()
        ]

        count_query = f"""
            SELECT COUNT(DISTINCT COALESCE(main.group_id, -main.id)) AS total
            FROM autokmdb_news main
            WHERE {where_main}
        """
        total_count = conn.execute(text(count_query), params).scalar() or 0

        if not page_ids:
            return total_count, []

        ids_list = ",".join(map(str, page_ids))
        full_query = f"""
            SELECT {main_article_cols}
            FROM autokmdb_news main
            LEFT JOIN users u ON main.mod_id = u.user_id
            WHERE main.id IN ({ids_list})
            ORDER BY {order_by_full}
        """
        main_articles = [
            dict(r) for r in conn.execute(text(full_query)).mappings()
        ]

        # Bulk fetch grouped articles for all groups on this page
        grouped_by_group_id: dict = {}
        page_group_ids = [a["group_id"] for a in main_articles if a["group_id"]]
        if page_group_ids:
            groups_list_page = ",".join(map(str, page_group_ids))
            main_ids_list = ",".join(
                str(a["id"]) for a in main_articles if a["group_id"]
            )
            bulk_group_query = f"""
                SELECT
                    n.group_id,
                    n.id, n.clean_url AS url, n.title, n.description,
                    CONVERT_TZ(n.article_date, @@session.time_zone, '+00:00') AS date,
                    n.newspaper_name, annotation_label, classification_label, negative_reason
                FROM autokmdb_news n
                WHERE n.group_id IN ({groups_list_page})
                  AND n.id NOT IN ({main_ids_list})
                ORDER BY n.group_id, n.id
            """
            for article in conn.execute(text(bulk_group_query)).mappings():
                grouped_by_group_id.setdefault(article["group_id"], []).append(dict(article))

    with engine.connect() as conn:
        recommended_tags = _bulk_fetch_recommended_tags(
            conn, [a["id"] for a in main_articles]
        )

    articles_with_groups = []
    for article in main_articles:
        article["groupedArticles"] = (
            grouped_by_group_id.get(article["group_id"], []) if article["group_id"] else []
        )
        article["recommended_tags"] = recommended_tags.get(
            article["id"], {"persons": [], "institutions": []}
        )
        articles_with_groups.append(article)

    return total_count, articles_with_groups


def force_accept_article(id: int, user_id: int) -> None:
    _execute(
        """UPDATE autokmdb_news SET classification_label = 1, processing_step = 4,
           skip_reason = NULL, source = 1, mod_id = :user_id WHERE id = :id""",
        {"user_id": user_id, "id": id},
    )


def retry_article(id: int) -> None:
    _execute(
        """UPDATE autokmdb_news
           SET skip_reason = NULL,
               processing_step = CASE WHEN COALESCE(text, '') = '' THEN 0 ELSE 1 END
           WHERE id = :id""",
        {"id": id},
    )


def annote_negative(id: int, reason: int, user_id: int) -> None:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT news_id FROM autokmdb_news WHERE id = :id"), {"id": id}
        ).first()
        news_id = row[0] if row else None

        conn.execute(
            text("""UPDATE autokmdb_news SET annotation_label = 0, processing_step = 5,
                    negative_reason = :reason, mod_id = :user_id WHERE id = :id"""),
            {"reason": reason, "user_id": user_id, "id": id},
        )

        if news_id:
            for query in [
                "DELETE FROM news_news WHERE news_id = :news_id",
                "DELETE FROM news_persons_link WHERE news_id = :news_id",
                "DELETE FROM news_institutions_link WHERE news_id = :news_id",
                "DELETE FROM news_places_link WHERE news_id = :news_id",
                "DELETE FROM news_others_link WHERE news_id = :news_id",
                "DELETE FROM news_lang WHERE news_id = :news_id",
            ]:
                conn.execute(text(query), {"news_id": news_id})


def clean_entity_name(name: str) -> str:
    """
    The KMDB admin splits tag lists on commas when an article is saved there, so a
    name containing a comma would be broken up into several new persons/institutions.
    """
    return re.sub(r"\s*,\s*", " ", name).strip()


def _create_tag(
    table: str, id_column: str, tag_type: str, name: str, user_id: int
) -> int:
    name = clean_entity_name(name)
    cre_time = int(datetime.now().timestamp())
    with engine.begin() as conn:
        existing = conn.execute(
            text(f"SELECT {id_column} FROM {table} WHERE name = :name"),
            {"name": name},
        ).scalar()
        if existing:
            logging.info(f"{tag_type} already exists with ID: {existing}")
            return existing

        db_id = conn.execute(
            text(f"""INSERT INTO {table} (status, name, cre_id, mod_id, import_id, cre_time, mod_time)
                     VALUES ('Y', :name, :user_id, :user_id, 0, :cre_time, :cre_time)"""),
            {"name": name, "user_id": user_id, "cre_time": cre_time},
        ).lastrowid
        conn.execute(
            text("""INSERT INTO tags_seo_data (seo_name, tag_type, item_id)
                    VALUES (:seo_name, :tag_type, :item_id)"""),
            {"seo_name": slugify(name), "tag_type": tag_type, "item_id": db_id},
        )
    return db_id


def create_person(name: str, user_id: int) -> int:
    logging.info("adding new person: " + name)
    return _create_tag("news_persons", "person_id", "persons", name, user_id)


def create_institution(name: str, user_id: int) -> int:
    logging.info("adding new institution: " + name)
    return _create_tag("news_institutions", "institution_id", "institutions", name, user_id)


def get_article_annotation(news_id):
    return _fetch_scalar(
        "SELECT annotation_label FROM autokmdb_news WHERE id = :id",
        {"id": news_id},
    )


def setTags(conn, news_id, persons, newspaper, institutions, places, others):
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

    tag_id = conn.execute(
        text("SELECT tag_id FROM news_tags WHERE news_id = :news_id"),
        {"news_id": news_id},
    ).scalar()

    if tag_id:
        conn.execute(
            text("UPDATE news_tags SET names = :names WHERE tag_id = :tag_id"),
            {"names": names_str, "tag_id": tag_id},
        )
        logging.info(f"updating tag_id={tag_id} news_id={news_id} with text: {names_str}")
    else:
        conn.execute(
            text("INSERT INTO news_tags (names, news_id) VALUES (:names, :news_id)"),
            {"names": names_str, "news_id": news_id},
        )
        logging.info(f"updating news_id={news_id} with text: {names_str}")


def annote_positive(
    id,
    source_url,
    source_url_string,
    title,
    description,
    text_content,
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
    Annotates an article as positive, creating or updating the necessary records.
    Handles entity linking and removes stale links.
    """
    cre_time = int(datetime.now().timestamp())
    category_dict = {0: 5, 1: 6, 2: 7, None: 5}
    alias = slugify(title)
    seo_url_default = "hirek/magyar-hirek/" + alias
    processed_text = text_content.replace("\n", "<br>")
    pub_timestamp = int(pub_date.timestamp())
    status_flag = "Y" if is_active else "N"

    # Leading/trailing whitespace in user-entered names would create duplicates
    # of existing persons/institutions, and commas get split by the KMDB admin,
    # so normalize before lookup.
    for entity in persons + institutions:
        if isinstance(entity.get("name"), str):
            entity["name"] = clean_entity_name(entity["name"])

    persons_to_create = [
        p for p in persons
        if ("db_id" not in p or not p["db_id"]) and p.get("name")
    ]
    institutions_to_create = [
        i for i in institutions
        if ("db_id" not in i or not i["db_id"]) and i.get("name")
    ]

    # Resolve / create missing person+institution db_ids (these commit separately,
    # matching the legacy behaviour where create_person/create_institution each
    # had their own commit).
    if persons_to_create:
        person_names = [p["name"] for p in persons_to_create]
        with engine.connect() as _conn:
            stmt = text(
                "SELECT person_id, name FROM news_persons WHERE name IN :names"
            ).bindparams(bindparam("names", expanding=True))
            existing_persons = {
                r["name"]: r["person_id"]
                for r in _conn.execute(stmt, {"names": person_names}).mappings()
            }
        for person in persons_to_create:
            if person["name"] in existing_persons:
                person["db_id"] = existing_persons[person["name"]]
            else:
                person["db_id"] = create_person(person["name"], user_id)
                all_persons_by_id[person["db_id"]] = person["name"]

    if institutions_to_create:
        institution_names = [i["name"] for i in institutions_to_create]
        with engine.connect() as _conn:
            stmt = text(
                "SELECT institution_id, name FROM news_institutions WHERE name IN :names"
            ).bindparams(bindparam("names", expanding=True))
            existing_institutions = {
                r["name"]: r["institution_id"]
                for r in _conn.execute(stmt, {"names": institution_names}).mappings()
            }
        for institution in institutions_to_create:
            if institution["name"] in existing_institutions:
                institution["db_id"] = existing_institutions[institution["name"]]
            else:
                institution["db_id"] = create_institution(institution["name"], user_id)
                all_institutions_by_id[institution["db_id"]] = institution["name"]
                get_similar_institutions_index().add(
                    {"id": institution["db_id"], "name": institution["name"], "count": 0}
                )

    with engine.begin() as conn:
        news_id = conn.execute(
            text("SELECT news_id FROM autokmdb_news WHERE id = :id"), {"id": id}
        ).scalar()
        is_update = bool(news_id)

        if is_update:
            conn.execute(
                text("""UPDATE news_news SET source_url = :source_url,
                        source_url_string = :source_url_string,
                        mod_time = :cre_time, mod_id = :user_id, status = :status
                        WHERE news_id = :news_id"""),
                {
                    "source_url": source_url, "source_url_string": source_url_string,
                    "cre_time": cre_time, "user_id": user_id,
                    "status": status_flag, "news_id": news_id,
                },
            )
            for q in [
                "DELETE FROM news_persons_link WHERE news_id = :news_id",
                "DELETE FROM news_institutions_link WHERE news_id = :news_id",
                "DELETE FROM news_places_link WHERE news_id = :news_id",
                "DELETE FROM news_others_link WHERE news_id = :news_id",
                "DELETE FROM news_files_link WHERE news_id = :news_id",
            ]:
                conn.execute(text(q), {"news_id": news_id})
        else:
            news_id = conn.execute(
                text("""INSERT INTO news_news (source_url, source_url_string, cre_time,
                        mod_time, pub_time, cre_id, mod_id, status, news_type, news_rel)
                        VALUES (:source_url, :source_url_string, :cre_time, :cre_time,
                                :pub_time, :user_id, :user_id, :status, 'D', 'N')"""),
                {
                    "source_url": source_url, "source_url_string": source_url_string,
                    "cre_time": cre_time, "pub_time": pub_timestamp,
                    "user_id": user_id, "status": status_flag,
                },
            ).lastrowid

        conn.execute(
            text("""UPDATE autokmdb_news SET annotation_label = 1, processing_step = 5,
                    news_id = :news_id, title = :title, description = :description,
                    text = :text, mod_id = :user_id, category = :category
                    WHERE id = :id"""),
            {
                "news_id": news_id, "title": title, "description": description,
                "text": text_content, "user_id": user_id, "category": category, "id": id,
            },
        )

        conn.execute(
            text("""REPLACE INTO seo_urls_data (seo_url, modul, action, item_id, lang)
                    VALUES (:seo_url, 'news', 'view', :item_id, 'hu')"""),
            {"seo_url": seo_url_default, "item_id": news_id},
        )

        if is_update:
            conn.execute(
                text("""UPDATE news_lang SET lang = 'hu', name = :name, teaser = :teaser,
                        articletext = :body, alias = :alias, seo_url_default = :seo
                        WHERE news_id = :news_id"""),
                {
                    "name": title, "teaser": description, "body": processed_text,
                    "alias": alias, "seo": seo_url_default, "news_id": news_id,
                },
            )
            conn.execute(
                text("UPDATE news_newspapers_link SET newspaper_id = :np WHERE news_id = :news_id"),
                {"np": newspaper_id, "news_id": news_id},
            )
            conn.execute(
                text("UPDATE news_categories_link SET cid = :cid, head = 'Y' WHERE news_id = :news_id"),
                {"cid": category_dict[category], "news_id": news_id},
            )
        else:
            conn.execute(
                text("""INSERT INTO news_lang (news_id, lang, name, teaser, articletext, alias, seo_url_default)
                        VALUES (:news_id, 'hu', :name, :teaser, :body, :alias, :seo)"""),
                {
                    "news_id": news_id, "name": title, "teaser": description,
                    "body": processed_text, "alias": alias, "seo": seo_url_default,
                },
            )
            conn.execute(
                text("INSERT INTO news_newspapers_link (news_id, newspaper_id) VALUES (:news_id, :np)"),
                {"news_id": news_id, "np": newspaper_id},
            )
            conn.execute(
                text("INSERT INTO news_categories_link (news_id, cid, head) VALUES (:news_id, :cid, 'Y')"),
                {"news_id": news_id, "cid": category_dict[category]},
            )

        # Collect unique entity IDs and per-entity annotation updates.
        unique_person_ids, unique_institution_ids, unique_place_ids = set(), set(), set()
        person_updates, institution_updates, place_updates = [], [], []

        for person in persons:
            if person.get("db_id"):
                unique_person_ids.add(person["db_id"])
            if isinstance(person.get("id"), int):
                person_updates.append(person["id"])
        for institution in institutions:
            if institution.get("db_id"):
                unique_institution_ids.add(institution["db_id"])
            if isinstance(institution.get("id"), int):
                institution_updates.append(institution["id"])
        for place in places:
            if place.get("db_id"):
                unique_place_ids.add(place["db_id"])
            if isinstance(place.get("id"), int):
                place_updates.append(place["id"])

        if unique_place_ids:
            parent_stmt = text(
                """SELECT parent_id FROM news_places
                   WHERE place_id IN :ids AND parent_id IS NOT NULL"""
            ).bindparams(bindparam("ids", expanding=True))
            for row in conn.execute(
                parent_stmt, {"ids": list(unique_place_ids)}
            ).mappings():
                if row["parent_id"]:
                    unique_place_ids.add(row["parent_id"])

        link_specs: list[tuple[str, list[dict]]] = []
        if unique_person_ids:
            link_specs.append((
                "INSERT INTO news_persons_link (news_id, person_id) VALUES (:news_id, :entity_id)",
                [{"news_id": news_id, "entity_id": pid} for pid in unique_person_ids],
            ))
        if unique_institution_ids:
            link_specs.append((
                "INSERT INTO news_institutions_link (news_id, institution_id) VALUES (:news_id, :entity_id)",
                [{"news_id": news_id, "entity_id": iid} for iid in unique_institution_ids],
            ))
        if unique_place_ids:
            link_specs.append((
                "INSERT INTO news_places_link (news_id, place_id) VALUES (:news_id, :entity_id)",
                [{"news_id": news_id, "entity_id": pid} for pid in unique_place_ids],
            ))
        other_links = [
            {"news_id": news_id, "entity_id": o["db_id"]}
            for o in others if o.get("db_id")
        ]
        if other_links:
            link_specs.append((
                "INSERT INTO news_others_link (news_id, other_id) VALUES (:news_id, :entity_id)",
                other_links,
            ))
        if file_ids:
            link_specs.append((
                "INSERT INTO news_files_link (news_id, file_id) VALUES (:news_id, :entity_id)",
                [{"news_id": news_id, "entity_id": fid} for fid in file_ids],
            ))

        for query, data in link_specs:
            try:
                conn.execute(text(query), data)
                logging.info(f"Successfully inserted {len(data)} records for: {query.split()[2]}")
            except Exception as e:
                logging.error(f"Error inserting data with query {query}: {e}")
                logging.error(f"Data sample: {data[:3] if len(data) > 3 else data}")
                raise

        # Reset annotation_label=0 on all autokmdb_* entities for this article.
        for table in ("autokmdb_persons", "autokmdb_institutions",
                      "autokmdb_places", "autokmdb_others", "autokmdb_files"):
            conn.execute(
                text(f"UPDATE {table} SET annotation_label = 0 WHERE autokmdb_news_id = :id"),
                {"id": id},
            )

        # Re-set annotation_label=1 for entities present in the request.
        def _set_labels_one(table: str, ids: list[int]) -> None:
            if ids:
                conn.execute(
                    text(f"UPDATE {table} SET annotation_label = 1 WHERE id = :id"),
                    [{"id": i} for i in ids],
                )

        _set_labels_one("autokmdb_persons", person_updates)
        _set_labels_one("autokmdb_institutions", institution_updates)
        _set_labels_one("autokmdb_places", place_updates)
        _set_labels_one("autokmdb_others", [
            o["id"] for o in others if isinstance(o.get("id"), int)
        ])
        _set_labels_one("autokmdb_files", [
            fid for fid in file_ids if isinstance(fid, int)
        ])

        # Remember the institution chosen for a detection that was not linked to the db (e.g. a
        # suggested similar one), otherwise it would show up unlinked again when re-editing.
        institution_links = [
            {"id": i["id"], "db_id": i["db_id"], "db_name": i.get("db_name") or i.get("name")}
            for i in institutions
            if isinstance(i.get("id"), int) and i.get("db_id")
        ]
        if institution_links:
            conn.execute(
                text("""UPDATE autokmdb_institutions
                        SET institution_id = :db_id, institution_name = :db_name
                        WHERE id = :id AND (institution_id IS NULL OR institution_id = 0)"""),
                institution_links,
            )

        setTags(conn, news_id, persons, newspaper_name, institutions, places, others)


def save_ner_step(id):
    _execute("UPDATE autokmdb_news SET processing_step = 3 WHERE id = :id", {"id": id})


def save_keyword_step(id):
    _execute("UPDATE autokmdb_news SET processing_step = 4 WHERE id = :id", {"id": id})


def get_rss_urls() -> list[dict]:
    return _fetch_all_dicts(
        'SELECT newspaper_id as id, name, rss_url FROM news_newspapers WHERE status = "Y"'
    )


@cache
def get_keyword_synonyms() -> list[dict]:
    return _fetch_all_dicts(
        "SELECT synonym, name, db_id FROM autokmdb_keyword_synonyms"
    )


def update_session(session_id: Optional[str], unix_timestamp: int):
    new_unix_timestamp = int(
        (datetime.fromtimestamp(unix_timestamp) + timedelta(minutes=30)).timestamp()
    )
    _execute(
        "UPDATE users_sessions SET session_expires = :expires WHERE session_id = :id",
        {"expires": new_unix_timestamp, "id": session_id},
    )


def validate_session(session_id: Optional[str]):
    if "NO_LOGIN" in os.environ:
        return True
    session = _fetch_one_dict(
        "SELECT * FROM users_sessions WHERE session_id = :id", {"id": session_id}
    )
    if session is None or session["registered"] == 0:
        return None
    update_session(session_id, session["session_expires"])
    return session["registered"]


def get_roles(session_id: int):
    session = _fetch_one_dict(
        "SELECT * FROM users_sessions WHERE session_id = :id", {"id": session_id}
    )
    if session is None or session["registered"] == 0:
        return []
    rows = _fetch_all_dicts(
        "SELECT * FROM users_modul_rights WHERE user_id = :user_id",
        {"user_id": session["registered"]},
    )
    return [
        {
            "modul_name": r["modul_name"],
            "action_name": r["action_name"],
            "action_right": r["action_right"],
        }
        for r in rows
    ]


def validate_user_credentials(username: str, password: str) -> Optional[int]:
    """Validate user credentials (MD5). Returns user_id if valid, else None."""
    import hashlib
    password_hash = hashlib.md5(password.encode("utf-8")).hexdigest()
    return _fetch_scalar(
        """SELECT user_id FROM users
           WHERE uname = :username AND upass = :password_hash AND ustatus = 'Y'""",
        {"username": username, "password_hash": password_hash},
    )


def create_user_session(user_id: int) -> str:
    """Create a new 8-hour session for the user. Returns the session ID."""
    import secrets
    import time
    import string

    alphabet = string.ascii_letters + string.digits
    session_id = "".join(secrets.choice(alphabet) for _ in range(32))
    expires_time = int(time.time()) + (8 * 60 * 60)

    _execute(
        """INSERT INTO users_sessions (session_id, registered, session_expires)
           VALUES (:session_id, :user_id, :expires)""",
        {"session_id": session_id, "user_id": user_id, "expires": expires_time},
    )
    return session_id


# Entity descriptions

KMDB_URL = os.environ.get("KMDB_URL", "https://adatbazis.k-monitor.hu")

# KMDB tables of the entity types that can get a generated description. Each has HTML teaser and
# bodytext columns and a <table>_link table to news_news, and every tag page is at
# /adatbazis/cimkek/<seo_name> from tags_seo_data.
DESCRIPTION_ENTITY_TABLES: dict[str, dict[str, str]] = {
    "person": {
        "table": "news_persons",
        "id": "person_id",
        "name": "name",
        "tag_type": "persons",
    },
    "institution": {
        "table": "news_institutions",
        "id": "institution_id",
        "name": "name",
        "tag_type": "institutions",
    },
    "file": {
        "table": "news_files",
        "id": "file_id",
        "name": "name_hu",
        "tag_type": "files",
    },
    "newspaper": {
        "table": "news_newspapers",
        "id": "newspaper_id",
        "name": "name",
        "tag_type": "newspapers",
    },
}

# Statuses of the autokmdb_entity_descriptions rows shown on each tab of the descriptions page.
DESCRIPTION_LIST_STATUSES: dict[str, Optional[list[str]]] = {
    "review": ["review"],
    "processing": ["queued"],
    "all": None,
}
DESCRIPTIONS_PAGE_SIZE = 20


def _execute_rowcount(query: str, params: Optional[dict] = None) -> int:
    """Execute an UPDATE/DELETE in a transaction and return the number of affected rows."""
    with engine.begin() as conn:
        return conn.execute(text(query), params or {}).rowcount


def html_to_text(html: Optional[str]) -> str:
    """Plain text of the HTML stored in the KMDB (teasers, bodytexts), keeping line breaks."""
    if not html:
        return ""
    if "<" not in html:
        return html.strip()
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "li", "h1", "h2", "h3", "h4", "tr"]):
        block.append("\n\n")
    return re.sub(r"\n\s*\n+", "\n\n", soup.get_text()).strip()


# Raw HTML in the markdown is escaped, the descriptions are shown on the public KMDB site.
_markdown = MarkdownIt("js-default")
# [url] source citations with the spaces before them, sometimes with several comma separated URLs,
# but not markdown links.
_CITATION = re.compile(r"[ \t]*\[(\s*https?://[^\s\]]+(?:\s*,\s*https?://[^\s\]]+)*\s*)\](?!\()")


# Formatting kept from the HTML edited on the descriptions page, the same as its editor allows.
_DESCRIPTION_TAGS = {"p", "br", "strong", "b", "em", "i", "u", "s", "a", "ul", "ol", "li"}


def is_kmdb_url(url: str) -> bool:
    """The KMDB is not a source of its own descriptions."""
    return urlparse(url).hostname == urlparse(KMDB_URL).hostname


def _citation_link(url: str) -> str:
    """Markdown link of a source shown as [domain], e.g. [atlatszo.hu]."""
    domain = (urlparse(url).hostname or url).removeprefix("www.")
    return f"[\\[{domain}\\]](<{url}>)"


def markdown_to_html(markdown: str) -> str:
    """
    HTML of a generated markdown description. Each [url] citation becomes a link shown as [domain],
    also when the model put several URLs in one bracket, and the citations of the KMDB are dropped.
    """

    def link_citation(match: re.Match) -> str:
        urls = re.split(r"\s*,\s*(?=https?://)", match.group(1).strip())
        return "".join(f" {_citation_link(url)}" for url in urls if not is_kmdb_url(url))

    return _markdown.render(_CITATION.sub(link_citation, markdown)).strip()


def sanitize_description_html(html: str) -> str:
    """The reviewed HTML is published on the KMDB site, so only the formatting of the editor is kept."""
    cleaned = nh3.clean(
        html,
        tags=_DESCRIPTION_TAGS,
        attributes={"a": {"href", "target"}},
        url_schemes={"http", "https", "mailto"},
    )
    # The editor wraps the content of list items in paragraphs and can leave empty paragraphs.
    soup = BeautifulSoup(cleaned, "html.parser")
    for item in soup.find_all("li"):
        children = [c for c in item.contents if not (isinstance(c, str) and not c.strip())]
        if len(children) == 1 and children[0].name == "p":
            children[0].unwrap()
    for paragraph in soup.find_all("p"):
        if not paragraph.get_text(strip=True):
            paragraph.decompose()
    return str(soup).strip()


def _combined_description(teaser: str, bodytext: str) -> str:
    """
    Both the teaser and the bodytext are overwritten by the new description, so both are kept for
    the prompt, unless the teaser is just repeated in the bodytext.
    """
    if not teaser or " ".join(teaser.split()) in " ".join(bodytext.split()):
        return bodytext
    if not bodytext:
        return teaser
    return f"{teaser}\n\n{bodytext}"


def get_description_entity(entity_type: str, entity_id: int) -> Optional[dict]:
    """
    Returns:
        Dict with the 'id', 'name', 'teaser' and 'bodytext' (plain text), the two combined as the
        current 'description' and the KMDB 'url' of the entity, or None if it does not exist.
    """
    tables = DESCRIPTION_ENTITY_TABLES[entity_type]
    row = _fetch_one_dict(
        f"""SELECT e.{tables['id']} AS id, e.{tables['name']} AS name, e.teaser, e.bodytext,
                   tsd.seo_name
            FROM {tables['table']} e
            LEFT JOIN tags_seo_data tsd
                ON tsd.item_id = e.{tables['id']} AND tsd.tag_type = :tag_type
            WHERE e.{tables['id']} = :id
            LIMIT 1""",
        {"id": entity_id, "tag_type": tables["tag_type"]},
    )
    if row is None:
        return None
    seo_name = row.pop("seo_name")
    row["url"] = f"{KMDB_URL}/adatbazis/cimkek/{seo_name}" if seo_name else None
    row["teaser"] = html_to_text(row["teaser"])
    row["bodytext"] = html_to_text(row["bodytext"])
    row["description"] = _combined_description(row["teaser"], row["bodytext"])
    return row


_DESCRIPTION_ARTICLE_COLUMNS = """
    n.news_id,
    nl.name AS title,
    nl.teaser,
    n.source_url,
    FROM_UNIXTIME(n.pub_time) AS date,
    MAX(nn.name) AS newspaper
"""
_DESCRIPTION_ARTICLE_JOINS = """
    JOIN news_lang nl ON nl.news_id = n.news_id AND nl.lang = 'hu'
    LEFT JOIN news_newspapers_link nnl ON nnl.news_id = n.news_id
    LEFT JOIN news_newspapers nn ON nn.newspaper_id = nnl.newspaper_id
"""


def _description_articles(rows: list[dict]) -> list[dict]:
    """Converts the article rows to plain text, oldest first."""
    articles = [
        {
            "news_id": r["news_id"],
            "title": " ".join(html_to_text(r["title"]).split()),
            "teaser": " ".join(html_to_text(r["teaser"]).split()),
            "url": r["source_url"],
            "date": r["date"].strftime("%Y-%m-%d") if r["date"] else "",
            "newspaper": r["newspaper"] or "",
        }
        for r in rows
    ]
    articles.sort(key=lambda a: a["date"])
    return articles


def get_description_articles(entity_type: str, entity_id: int, limit: int) -> list[dict]:
    """
    Returns:
        The latest (at most limit) active KMDB articles tagged with the entity, oldest first.
    """
    tables = DESCRIPTION_ENTITY_TABLES[entity_type]
    rows = _fetch_all_dicts(
        f"""SELECT {_DESCRIPTION_ARTICLE_COLUMNS}
            FROM {tables['table']}_link l
            JOIN news_news n ON n.news_id = l.news_id
            {_DESCRIPTION_ARTICLE_JOINS}
            WHERE l.{tables['id']} = :id AND n.status = 'Y'
            GROUP BY n.news_id
            ORDER BY n.pub_time DESC
            LIMIT {int(limit)}""",
        {"id": entity_id},
    )
    return _description_articles(rows)


def get_articles_mentioning(name: str, limit: int) -> list[dict]:
    """
    Newspapers are only linked to the articles they published, so the articles about them are
    found by their name in the title or the teaser.

    Returns:
        The latest (at most limit) active KMDB articles mentioning the name, oldest first.
    """
    rows = _fetch_all_dicts(
        f"""SELECT {_DESCRIPTION_ARTICLE_COLUMNS}
            FROM news_news n
            {_DESCRIPTION_ARTICLE_JOINS}
            WHERE n.status = 'Y' AND (nl.name LIKE :pattern OR nl.teaser LIKE :pattern)
            GROUP BY n.news_id
            ORDER BY n.pub_time DESC
            LIMIT {int(limit)}""",
        {"pattern": f"%{name}%"},
    )
    return _description_articles(rows)


def get_description_related(
    entity_type: str, entity_id: int, related_type: str, limit: int = 15
) -> list[dict]:
    """
    Returns:
        List of dicts with the 'name' and the number of common articles ('count') of the entities
        of related_type that are most often tagged together with the entity.
    """
    tables = DESCRIPTION_ENTITY_TABLES[entity_type]
    related = DESCRIPTION_ENTITY_TABLES[related_type]
    return _fetch_all_dicts(
        f"""SELECT r.{related['name']} AS name, COUNT(DISTINCT l.news_id) AS count
            FROM {tables['table']}_link l
            JOIN news_news n ON n.news_id = l.news_id AND n.status = 'Y'
            JOIN {related['table']}_link rl ON rl.news_id = l.news_id
            JOIN {related['table']} r ON r.{related['id']} = rl.{related['id']}
            WHERE l.{tables['id']} = :id AND r.status = 'Y'
            GROUP BY r.{related['id']}
            ORDER BY count DESC
            LIMIT {int(limit)}""",
        {"id": entity_id},
    )


def add_description_request(
    entity_type: str, entity_id: int, entity_name: str, user_id: int
) -> Optional[int]:
    """
    Queues the entity for description generation.

    Returns:
        Id of the new request, or None if the entity already has one that is queued or waiting
        for review.
    """
    with engine.begin() as conn:
        existing = conn.execute(
            text("""SELECT id FROM autokmdb_entity_descriptions
                    WHERE entity_type = :type AND entity_id = :id
                        AND status IN ('queued', 'review')
                    LIMIT 1"""),
            {"type": entity_type, "id": entity_id},
        ).scalar()
        if existing:
            return None
        return conn.execute(
            text("""INSERT INTO autokmdb_entity_descriptions
                        (entity_type, entity_id, entity_name, status, cre_id, mod_id, cre_time)
                    VALUES (:type, :id, :name, 'queued', :user_id, :user_id, NOW())"""),
            {"type": entity_type, "id": entity_id, "name": entity_name, "user_id": user_id},
        ).lastrowid


def get_next_description_request() -> Optional[dict]:
    return _fetch_one_dict(
        """SELECT id, entity_type, entity_id, entity_name FROM autokmdb_entity_descriptions
           WHERE status = 'queued'
           ORDER BY cre_time, id
           LIMIT 1"""
    )


def save_description_suggestion(
    id: int,
    suggestion: str,
    sources: list[dict],
    prompt: str,
    model: str,
    token_counts: dict,
) -> None:
    _execute(
        """UPDATE autokmdb_entity_descriptions
           SET status = 'review', suggestion = :suggestion, final_description = NULL, sources = :sources,
               prompt = :prompt, model = :model, error = NULL, prompt_tokens = :prompt_tokens,
               response_tokens = :response_tokens, thinking_tokens = :thinking_tokens
           WHERE id = :id""",
        {
            "id": id,
            "suggestion": suggestion,
            "sources": json.dumps(sources, ensure_ascii=False),
            "prompt": prompt,
            "model": model,
            "prompt_tokens": token_counts.get("prompt"),
            "response_tokens": token_counts.get("response"),
            "thinking_tokens": token_counts.get("thinking"),
        },
    )


def save_description_error(id: int, error: str) -> None:
    _execute(
        "UPDATE autokmdb_entity_descriptions SET status = 'error', error = :error WHERE id = :id",
        {"id": id, "error": error},
    )


def get_description_counts() -> dict[str, int]:
    rows = _fetch_all_dicts(
        "SELECT status, COUNT(*) AS count FROM autokmdb_entity_descriptions GROUP BY status"
    )
    by_status = {r["status"]: r["count"] for r in rows}
    return {
        key: sum(by_status.values()) if statuses is None
        else sum(by_status.get(s, 0) for s in statuses)
        for key, statuses in DESCRIPTION_LIST_STATUSES.items()
    }


def get_descriptions(status_key: str, page: int) -> tuple[int, list[dict]]:
    """
    Returns:
        Number of all rows with the statuses of the tab, and the rows of the given page, newest
        first.
    """
    statuses = DESCRIPTION_LIST_STATUSES[status_key]
    where = "WHERE d.status IN :statuses" if statuses else ""
    params = {"statuses": statuses} if statuses else {}
    offset = (max(page, 1) - 1) * DESCRIPTIONS_PAGE_SIZE

    count_stmt = text(f"SELECT COUNT(*) FROM autokmdb_entity_descriptions d {where}")
    list_stmt = text(
        f"""SELECT d.id, d.entity_type, d.entity_id, d.entity_name, d.status, d.error,
                   LEFT(d.final_description, 2000) AS final_preview,
                   LEFT(d.suggestion, 2000) AS suggestion_preview,
                   d.cre_time, d.mod_time, u.name AS mod_name
            FROM autokmdb_entity_descriptions d
            LEFT JOIN users u ON d.mod_id = u.user_id
            {where}
            ORDER BY d.id DESC
            LIMIT {DESCRIPTIONS_PAGE_SIZE} OFFSET {int(offset)}"""
    )
    if statuses:
        count_stmt = count_stmt.bindparams(bindparam("statuses", expanding=True))
        list_stmt = list_stmt.bindparams(bindparam("statuses", expanding=True))
    with engine.connect() as conn:
        length = conn.execute(count_stmt, params).scalar()
        rows = [dict(r) for r in conn.execute(list_stmt, params).mappings()]
    for row in rows:
        final_preview, suggestion_preview = row.pop("final_preview"), row.pop("suggestion_preview")
        if final_preview:
            preview = html_to_text(final_preview)
        else:
            preview = html_to_text(markdown_to_html(suggestion_preview or ""))
        row["preview"] = " ".join(preview.split())[:300]
    return length, rows


def get_description(id: int) -> Optional[dict]:
    row = _fetch_one_dict(
        """SELECT d.*, u.name AS mod_name
           FROM autokmdb_entity_descriptions d
           LEFT JOIN users u ON d.mod_id = u.user_id
           WHERE d.id = :id""",
        {"id": id},
    )
    if row is not None:
        row["sources"] = json.loads(row["sources"]) if row["sources"] else []
        row["suggestion_html"] = markdown_to_html(row["suggestion"]) if row["suggestion"] else ""
    return row


def accept_description(id: int, description_html: str, user_id: int) -> bool:
    """
    Writes the reviewed HTML of a suggestion, sanitized, to both the teaser and the bodytext of the
    entity in the KMDB, and keeps their previous HTML in the request as a backup.

    Returns:
        False if the request was not waiting for review or the entity no longer exists.
    """
    with engine.begin() as conn:
        request = conn.execute(
            text("""SELECT entity_type, entity_id FROM autokmdb_entity_descriptions
                    WHERE id = :id AND status = 'review'
                    FOR UPDATE"""),
            {"id": id},
        ).mappings().first()
        if request is None:
            return False

        tables = DESCRIPTION_ENTITY_TABLES[request["entity_type"]]
        old = conn.execute(
            text(f"""SELECT teaser, bodytext FROM {tables['table']}
                     WHERE {tables['id']} = :entity_id
                     FOR UPDATE"""),
            {"entity_id": request["entity_id"]},
        ).mappings().first()
        if old is None:
            return False

        description_html = sanitize_description_html(description_html)
        conn.execute(
            text(f"""UPDATE {tables['table']} SET teaser = :html, bodytext = :html
                     WHERE {tables['id']} = :entity_id"""),
            {"html": description_html, "entity_id": request["entity_id"]},
        )
        conn.execute(
            text("""UPDATE autokmdb_entity_descriptions
                    SET status = 'accepted', final_description = :text,
                        old_teaser = :old_teaser, old_bodytext = :old_bodytext, mod_id = :user_id
                    WHERE id = :id"""),
            {
                "id": id,
                "text": description_html,
                "old_teaser": old["teaser"],
                "old_bodytext": old["bodytext"],
                "user_id": user_id,
            },
        )
    return True


def reject_description(id: int, user_id: int) -> bool:
    return _execute_rowcount(
        """UPDATE autokmdb_entity_descriptions SET status = 'rejected', mod_id = :user_id
           WHERE id = :id AND status = 'review'""",
        {"id": id, "user_id": user_id},
    ) > 0


def requeue_description(id: int, user_id: int) -> bool:
    """Queues a request again to regenerate its suggestion."""
    return _execute_rowcount(
        """UPDATE autokmdb_entity_descriptions
           SET status = 'queued', error = NULL, mod_id = :user_id
           WHERE id = :id AND status IN ('review', 'rejected', 'error')""",
        {"id": id, "user_id": user_id},
    ) > 0
