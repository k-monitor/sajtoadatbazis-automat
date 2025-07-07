from typing import Optional
from flask import Response, jsonify, Blueprint, request
from auto_kmdb import db
from math import ceil
import logging
from datetime import datetime
import csv
import io


with db.connection_pool.get_connection() as connection:
    keyword_synonyms: list[dict] = db.get_keyword_synonyms(connection)

api = Blueprint("api", __name__, url_prefix="/api")
all_domains: list[dict] = db.get_all_newspapers()

def get_session_id(request) -> Optional[str]:
    return request.headers.get("Authorization")


@api.route("/keyword_synonyms", methods=["GET"])
def get_keyword_synonyms():
    return jsonify(keyword_synonyms), 200


@api.route("/articles_by_day.csv", methods=["GET"])
def get_articles_by_day():
    content: Optional[dict] = request.args
    start: str = content.get("from", "2000-01-01")
    end: str = content.get("to", "2050-01-01")
    newspaper_id: Optional[int] = content.get("newspaper_id", None)
    with db.connection_pool.get_connection() as connection:
        articles_by_day: list[dict] = db.get_articles_by_day(newspaper_id)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=articles_by_day[0].keys())

        writer.writeheader()
        writer.writerows(articles_by_day)

        output.seek(0)
        response = Response(output, mimetype="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=data.csv"

        return response


@api.route("/articles_by_day", methods=["GET"])
def get_articles_by_day_json():
    content: Optional[dict] = request.args
    start: str = content.get("from", "2000-01-01")
    end: str = content.get("to", "2050-01-01")
    newspaper_id: Optional[int] = content.get("newspaper_id", None)
    with db.connection_pool.get_connection() as connection:
        articles_by_day: list[dict] = db.get_articles_by_day(newspaper_id)
        for article in articles_by_day:
            if "date" in article and type(article["date"]) == datetime:
                article["date"] = article["date"].strftime("%Y-%m-%d")
        return jsonify(articles_by_day), 200


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
    domain_ids: list[int] = [domain["id"] for domain in domains] if domains else [-1]
    skip_reasin: int = content.get("skip_reason", -1)

    with db.connection_pool.get_connection() as connection:
        article_counts = db.get_article_counts(
            connection, domain_ids, "%" + q + "%", start, end, skip_reasin
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
    domain_ids: list[int] = [domain["id"] for domain in domains] if domains else [-1]
    reverse: bool = content.get("reverse", False)
    skip_reasin: int = content.get("skip_reason", -1)

    with db.connection_pool.get_connection() as connection:
        article_response = db.get_articles(
            connection,
            page,
            status,
            domain_ids,
            "%" + q + "%",
            start,
            end,
            reverse,
            skip_reasin,
        )
        if article_response is None:
            return jsonify({"error": "Hiba a lekérés során!"}), 500
        length, articles = article_response
        articles = db.group_articles(articles)
        logging.info(f"articles: {articles}")

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


@api.route("/process_and_accept", methods=["POST"])
def process_and_accept():
    session_id: Optional[str] = get_session_id(request)
    with db.connection_pool.get_connection() as connection:
        user_id = db.validate_session(connection, session_id)
        if not user_id:
            return jsonify({"error": "Nem vagy bejelentkezve!"}), 401

    content: Optional[dict] = request.json

    if not content:
        return jsonify({}), 400

    with db.connection_pool.get_connection() as connection:
        article_id: int = content["article_id"]
        db.process_and_accept_article(connection, article_id, user_id)
        return jsonify({}), 200


@api.route("/annote/pick_out", methods=["POST"])
def pick_out():
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
        db.pick_out_article(connection, id, user_id)
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

    content: Optional[dict] = request.json

    if not content:
        return jsonify({}), 400

    url = content["url"]
    title = content["title"]
    description = content["description"]
    text = content["text"]
    persons = content["positive_persons"]
    institutions = content["positive_institutions"]
    places = content["positive_places"]
    others = content["tags"]
    newspaper_id = content["newspaper_id"]
    newspaper_name = content["newspaper_name"]
    is_active = content["active"]
    pub_date = content["pub_date"]
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
            "manual",
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

    return (
        jsonify(
            {
                "person": db.get_all_persons_freq(),
                "institution": db.get_all_institutions_freq(),
                "place": db.get_all_places_freq(),
                "keywords": db.get_all_others_freq(),
                "domains": db.get_all_newspapers(),
                "files": db.get_all_files(),
            }
        ),
        200,
    )


@api.route("/domains", methods=["GET"])
def domains():
    session_id: Optional[str] = get_session_id(request)

    return (
        jsonify(
            {
                "domains": all_domains,
            }
        ),
        200,
    )


@api.route("/status")
def hello():
    return "OK"


@api.route("/login", methods=["POST"])
def login():
    """
    Authenticate user and create session.
    Expects JSON with 'username' and 'password' fields.
    Sets session cookie on successful authentication.
    """
    content: Optional[dict] = request.json
    
    if not content:
        return jsonify({"error": "Missing request body"}), 400
    
    username: str = content.get("username", "")
    password: str = content.get("password", "")
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    with db.connection_pool.get_connection() as connection:
        # Validate credentials
        user_id = db.validate_user_credentials(connection, username, password)
        
        if not user_id:
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Create session
        session_id = db.create_user_session(connection, user_id)
        
        # Create response
        response = jsonify({"success": True, "message": "Login successful", "session_id": session_id})
        
        return response, 200
