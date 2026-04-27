from functools import cache
from typing import Literal, Any, Optional
from mysql.connector.pooling import MySQLConnectionPool
import os
from slugify import slugify
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from cachetools import cached, LRUCache, TTLCache
from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

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

engine: Engine = create_engine(
    "mysql+mysqlconnector://",
    creator=lambda: connection_pool.get_connection(),
    poolclass=NullPool,
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


@cached(cache=TTLCache(maxsize=32, ttl=3600))
def get_articles_by_day(
    newspaper_id: Optional[int] = None
) -> list[dict]:
    newspaper_condition = "WHERE newspaper_id = :newspaper_id" if newspaper_id else ""
    params = {"newspaper_id": newspaper_id} if newspaper_id else {}

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
        WHERE n.source_url = :source_url
        LIMIT 1
    """
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
            text(find_query), {"source_url": source_url}
        ).mappings().first()
        if not main_row:
            return None

        main_article = dict(main_row)
        group_id = main_article.get("group_id")
        _attach_article_entities(conn, main_article)

        grouped_articles: list[dict] = []
        if group_id is not None:
            rows = conn.execute(
                text(group_query),
                {"group_id": group_id, "main_id": main_article["id"]},
            ).mappings()
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

    return article


def group_articles(articles):
    """
    This function is no longer needed as the get_articles function now handles grouping internally.
    Kept for backward compatibility but just returns articles as-is.
    """
    return articles


def get_article_counts(
    domains: list[int],
    search_query="",
    start="2000-01-01",
    end="2050-01-01",
    skip_reason: int = -1,
    is_url_search: bool = False,
    cleaned_url: str = "",
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

    where_clause = " AND ".join(conditions)
    where_main = where_clause.replace("n.", "main.")

    # Sort configuration
    sort_order = "ASC" if reverse else "DESC"
    sort_field = (
        "main.source DESC, main.article_date"
        if status != "positive"
        else "main.article_date"
    )
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
        if has_text_search:
            # For text searches, first get matching IDs efficiently
            match_query = f"""
                SELECT main.id, main.group_id
                FROM autokmdb_news main
                WHERE {where_main}
            """
            matching_rows = [
                dict(r) for r in conn.execute(text(match_query), params).mappings()
            ]
            if not matching_rows:
                return 0, []

            matching_group_ids = {r["group_id"] for r in matching_rows if r["group_id"]}

            group_main_ids: set = set()
            if matching_group_ids:
                groups_list = ",".join(map(str, matching_group_ids))
                rows = conn.execute(text(f"""
                    SELECT MIN(id) as main_id, group_id
                    FROM autokmdb_news
                    WHERE group_id IN ({groups_list})
                    GROUP BY group_id
                """)).mappings()
                for row in rows:
                    group_main_ids.add(row["main_id"])

            ungrouped_match_ids = {
                r["id"] for r in matching_rows if r["group_id"] is None
            }
            display_ids = ungrouped_match_ids | group_main_ids
            if not display_ids:
                return 0, []

            total_count = len(display_ids)
            ids_list = ",".join(map(str, display_ids))
            paginated_query = f"""
                SELECT {main_article_cols}
                FROM autokmdb_news main
                LEFT JOIN users u ON main.mod_id = u.user_id
                WHERE main.id IN ({ids_list})
                ORDER BY {sort_field} {sort_order}
                LIMIT 10 OFFSET {offset}
            """
            main_articles = [
                dict(r) for r in conn.execute(text(paginated_query)).mappings()
            ]
        else:
            # Non-search query: find qualifying groups first
            qualifying_groups_query = f"""
                SELECT DISTINCT n.group_id
                FROM autokmdb_news n
                WHERE n.group_id IS NOT NULL AND {where_clause}
            """
            qualifying_groups = [
                row["group_id"] for row in
                conn.execute(text(qualifying_groups_query), params).mappings()
            ]

            if qualifying_groups:
                groups_list = ",".join(map(str, qualifying_groups))
                group_condition = f"main.group_id IN ({groups_list})"
            else:
                group_condition = "FALSE"

            count_query = f"""
                SELECT COUNT(*) as total_count
                FROM autokmdb_news main
                WHERE (main.group_id IS NULL
                       OR main.id = (SELECT MIN(n3.id) FROM autokmdb_news n3 WHERE n3.group_id = main.group_id))
                  AND (
                      (main.group_id IS NULL AND ({where_main}))
                      OR
                      (main.group_id IS NOT NULL AND {group_condition})
                  )
            """
            total_count = conn.execute(text(count_query), params).scalar()

            paginated_query = f"""
                SELECT {main_article_cols}
                FROM autokmdb_news main
                LEFT JOIN users u ON main.mod_id = u.user_id
                WHERE (main.group_id IS NULL
                       OR main.id = (SELECT MIN(n3.id) FROM autokmdb_news n3 WHERE n3.group_id = main.group_id))
                  AND (
                      (main.group_id IS NULL AND ({where_main}))
                      OR
                      (main.group_id IS NOT NULL AND {group_condition})
                  )
                ORDER BY {sort_field} {sort_order}
                LIMIT 10 OFFSET {offset}
            """
            main_articles = [
                dict(r) for r in conn.execute(text(paginated_query), params).mappings()
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

    articles_with_groups = []
    for article in main_articles:
        article["groupedArticles"] = (
            grouped_by_group_id.get(article["group_id"], []) if article["group_id"] else []
        )
        articles_with_groups.append(article)

    return total_count, articles_with_groups


def force_accept_article(id: int, user_id: int) -> None:
    _execute(
        """UPDATE autokmdb_news SET classification_label = 1, processing_step = 4,
           skip_reason = NULL, source = 1, mod_id = :user_id WHERE id = :id""",
        {"user_id": user_id, "id": id},
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


def _create_tag(
    table: str, id_column: str, tag_type: str, name: str, user_id: int
) -> int:
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
