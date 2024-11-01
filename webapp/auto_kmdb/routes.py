from typing import Optional
from flask import jsonify, Blueprint, request
from auto_kmdb import db
from math import ceil
import logging
from datetime import datetime


with db.connection_pool.get_connection() as connection:
    keyword_synonyms: list[dict] = db.get_keyword_synonyms(connection)

api = Blueprint("api", __name__, url_prefix="/api")


def get_session_id(request):
    return request.headers.get("Authorization")


@api.route("/keyword_synonyms", methods=["GET"])
def get_keyword_synonyms():
    return jsonify(keyword_synonyms), 200


@api.route("/article_counts", methods=["POST"])
def api_article_counts():
    session_id: Optional[str] = get_session_id(request)
    with db.connection_pool.get_connection() as connection:
        if not db.validate_session(connection, session_id):
            return jsonify({"error": "Nem vagy bejelentkezve!"}), 401

    content: Optional[dict] = request.json

    if not content:
        return jsonify({}), 400

    start: str = content.get("from", "2000-01-01")
    end: str = content.get("to", "2050-01-01")
    q: str = content.get("q", "")
    domains: dict = content["domain"]
    domain_ids: list[int] = [domain["id"] for domain in domains]

    with db.connection_pool.get_connection() as connection:
        article_counts = db.get_article_counts(
            connection, domain_ids, "%" + q + "%", start, end
        )

    return jsonify(article_counts), 200


@api.route("/article/<int:id>", methods=["GET"])
def api_article(id):
    session_id: Optional[str] = get_session_id(request)
    with db.connection_pool.get_connection() as connection:
        if not db.validate_session(connection, session_id):
            return jsonify({"error": "Nem vagy bejelentkezve!"}), 401

    with db.connection_pool.get_connection() as connection:
        article = db.get_article(connection, id)

    return jsonify(article), 200


@api.route("/articles", methods=["POST"])
def api_articles():
    logging.info("requesting api articles")
    session_id: Optional[str] = get_session_id(request)
    with db.connection_pool.get_connection() as connection:
        if not db.validate_session(connection, session_id):
            return jsonify({"error": "Nem vagy bejelentkezve!"}), 401

    content: Optional[dict] = request.json

    if not content:
        return jsonify({}), 400

    page: int = content.get("page", 1)
    status: str = content.get("status", "mixed")
    start: str = content.get("from", "2000-01-01")
    end: str = content.get("to", "2050-01-01")
    q: str = content.get("q", "")
    domains: dict = content["domain"]
    domain_ids: list[int] = [domain["id"] for domain in domains]
    reverse: bool = content.get("reverse", False)

    with db.connection_pool.get_connection() as connection:
        length, articles = db.get_articles(
            connection, page, status, domain_ids, "%" + q + "%", start, end, reverse
        )

    return jsonify({"pages": ceil(length / 10), "articles": articles}), 200


@api.route("/annote/negative", methods=["POST"])
def not_corruption():
    session_id: Optional[str] = get_session_id(request)
    with db.connection_pool.get_connection() as connection:
        user_id: Optional[int | bool] = db.validate_session(connection, session_id)
        if not user_id:
            return jsonify({"error": "Nem vagy bejelentkezve!"}), 401

    content: Optional[dict] = request.json

    if not content:
        return jsonify({}), 400

    id: int = content["id"]
    reason: int = content["reason"]
    with db.connection_pool.get_connection() as connection:
        db.annote_negative(connection, id, reason, user_id)
    return jsonify({}), 200


@api.route("/annote/force_accept", methods=["POST"])
def force_accept():
    session_id: Optional[str] = get_session_id(request)
    with db.connection_pool.get_connection() as connection:
        user_id: Optional[int | bool] = db.validate_session(connection, session_id)
        if not user_id:
            return jsonify({"error": "Nem vagy bejelentkezve!"}), 401

    content: Optional[dict] = request.json

    if not content:
        return jsonify({}), 400

    id: int = content["id"]
    with db.connection_pool.get_connection() as connection:
        db.force_accept_article(connection, id, user_id)
    return jsonify({}), 200


@api.route("/annote/positive", methods=["POST"])
@api.route("/change/positive", methods=["POST"])
@api.route("/edit/positive", methods=["POST"])
def annote():
    session_id: Optional[str] = get_session_id(request)
    with db.connection_pool.get_connection() as connection:
        user_id = db.validate_session(connection, session_id)
        if not user_id:
            return jsonify({"error": "Nem vagy bejelentkezve!"}), 401

    content: Optional[dict] = request.json

    if not content:
        return jsonify({}), 400

    id: int = content["id"]

    correct_annotations: dict[Optional[int], str] = {
        None: "/api/annote/positive",
        1: "/api/edit/positive",
        0: "/api/change/positive",
    }
    with db.connection_pool.get_connection() as connection:
        annotation_label: Optional[int] = db.get_article_annotation(connection, id)
    if request.path != correct_annotations[annotation_label]:
        return (
            jsonify(
                {
                    "error": "Szerkesztés közben megváltozott a cikk státusza. Kérlek töltsd újra az oldalt!"
                }
            ),
            409,
        )

    url = request.json["url"]
    title = request.json["title"]
    description = request.json["description"]
    text = request.json["text"]
    persons = request.json["positive_persons"]
    institutions = request.json["positive_institutions"]
    places = request.json["positive_places"]
    others = request.json["tags"]
    newspaper_id = request.json["newspaper_id"]
    newspaper_name = request.json["newspaper_name"]
    is_active = request.json["active"]
    pub_date = request.json["pub_date"]
    parsed_date = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
    category = 0
    if "category" in content:
        category: int = content["category"]
    file_ids = []
    if "file_ids" in content:
        file_ids: list[int] = content["file_ids"]

    with db.connection_pool.get_connection() as connection:
        if (
            db.url_exists_in_kmdb(connection, url)
            and request.path == "/api/annote/positive"
        ):
            return (
                jsonify(
                    {
                        "error": "Ez a cikk url alapján már szerepel az adatbázisban. Valószínűleg az autokmdb-n kívülről lett hozzáadva."
                    }
                ),
                409,
            )

    with db.connection_pool.get_connection() as connection:
        db.annote_positive(
            connection,
            id,
            url,
            title,
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
            parsed_date,
        )
    return jsonify({}), 200


@api.route("/add_url", methods=["POST"])
def add_url():
    session_id: Optional[str] = get_session_id(request)
    with db.connection_pool.get_connection() as connection:
        user_id = db.validate_session(connection, session_id)
        if not user_id:
            return jsonify({"error": "Nem vagy bejelentkezve!"}), 401

    content: Optional[dict] = request.json

    if not content:
        return jsonify({}), 400

    with db.connection_pool.get_connection() as connection:
        url: str = content["url"]
        if db.check_url_exists(connection, url):
            return jsonify({"error": "Cikk már létezik"}), 400
        db.init_news(
            connection,
            1,
            url,
            url,
            content["newspaper_name"],
            content["newspaper_id"],
            user_id,
            None,
        )
        return jsonify({}), 200


@api.route("/all_labels", methods=["GET"])
def all_labels():
    session_id: Optional[str] = get_session_id(request)
    with db.connection_pool.get_connection() as connection:
        if not db.validate_session(connection, session_id):
            return jsonify({"error": "Nem vagy bejelentkezve!"}), 401

    with db.connection_pool.get_connection() as connection:
        return (
            jsonify(
                {
                    "person": db.get_all_persons(connection),
                    "institution": db.get_all_institutions(connection),
                    "place": db.get_all_places(connection),
                    "keywords": db.get_all_others(connection),
                    "domains": db.get_all_newspapers(connection),
                    "files": db.get_all_files(connection),
                }
            ),
            200,
        )


@api.route("/status")
def hello():
    return "OK"
