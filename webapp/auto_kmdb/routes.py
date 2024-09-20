from flask import jsonify, Blueprint, request
from auto_kmdb.db import get_article, get_articles, annote_negative, connection_pool, force_accept_article, get_article_annotation
from auto_kmdb.db import get_all_persons, get_all_institutions, get_all_places, get_all_others, get_all_newspapers, get_all_files
from auto_kmdb.db import check_url_exists, url_exists_in_kmdb, init_news, annote_positive, get_article_counts, validate_session, get_keyword_synonyms
from math import ceil
import json
import logging
from datetime import datetime


with connection_pool.get_connection() as connection:
    keyword_synonyms = get_keyword_synonyms(connection)

api = Blueprint('api', __name__, url_prefix='/api')


def get_session_id(request):
    return request.cookies.get('PHPSESSID')


def reformat_article(article):
    try:
        article['persons'] = json.loads('['+article['persons']+']') if article['persons'] else []
    except Exception as e:
        print(e)
        article['persons'] = []
    try:
        article['institutions'] = json.loads('['+article['institutions']+']') if article['institutions'] else []
    except Exception as e:
        print(e)
        article['institutions'] = []
    try:
        article['places'] = json.loads('['+article['places']+']') if article['places'] else []
    except Exception as e:
        print(e)
        article['places'] = []
    try:
        article['others'] = json.loads('['+article['others']+']') if article['others'] else []
    except Exception as e:
        print(e)
        article['others'] = []

    return article


@api.route('/keyword_synonyms', methods=["GET"])
def get_keyword_synonyms():
    return jsonify(keyword_synonyms), 200


@api.route('/article_counts', methods=["POST"])
def api_article_counts():
    session_id = get_session_id(request)
    with connection_pool.get_connection() as connection:
        if not validate_session(connection, session_id):
            return jsonify({'error': 'Nem vagy bejelentkezve!'}), 401

    content: map = request.json

    start = content.get('from', '2000-01-01')
    end = content.get('to', '2050-01-01')
    q = content.get('q', '')
    domains = content['domain']
    domain_ids = [domain['id'] for domain in domains]

    with connection_pool.get_connection() as connection:
        article_counts = get_article_counts(connection, domain_ids, '%'+q+'%', start, end)

    return jsonify(article_counts), 200


@api.route('/article/<int:id>', methods=["GET"])
def api_article(id):
    session_id = get_session_id(request)
    with connection_pool.get_connection() as connection:
        if not validate_session(connection, session_id):
            return jsonify({'error': 'Nem vagy bejelentkezve!'}), 401

    with connection_pool.get_connection() as connection:
        article = get_article(connection, id)

    return jsonify(article), 200


@api.route('/articles', methods=["POST"])
def api_articles():
    logging.info('requesting api articles')
    session_id = get_session_id(request)
    with connection_pool.get_connection() as connection:
        if not validate_session(connection, session_id):
            return jsonify({'error': 'Nem vagy bejelentkezve!'}), 401

    content: map = request.json

    page = content.get('page', 1)
    status = content.get('status', 'mixed')
    start = content.get('from', '2000-01-01')
    end = content.get('to', '2050-01-01')
    q = content.get('q', '')
    domains = content['domain']
    domain_ids = [domain['id'] for domain in domains]
    reverse = content.get('reverse', False)

    with connection_pool.get_connection() as connection:
        length, articles = get_articles(connection, page, status, domain_ids, '%'+q+'%', start, end, reverse)

    return jsonify({'pages': ceil(length/10), 'articles': articles}), 200


@api.route('/annote/negative', methods=["POST"])
def not_corruption():
    session_id = get_session_id(request)
    with connection_pool.get_connection() as connection:
        user_id = validate_session(connection, session_id)
        if not user_id:
            return jsonify({'error': 'Nem vagy bejelentkezve!'}), 401

    id = request.json['id']
    reason = request.json['reason']
    with connection_pool.get_connection() as connection:
        annote_negative(connection, id, reason, user_id)
    return jsonify({}), 200


@api.route('/annote/force_accept', methods=["POST"])
def force_accept():
    session_id = get_session_id(request)
    with connection_pool.get_connection() as connection:
        user_id = validate_session(connection, session_id)
        if not user_id:
            return jsonify({'error': 'Nem vagy bejelentkezve!'}), 401

    id = request.json['id']
    with connection_pool.get_connection() as connection:
        force_accept_article(connection, id, user_id)
    return jsonify({}), 200


@api.route('/annote/positive', methods=["POST"])
@api.route('/change/positive', methods=["POST"])
@api.route('/edit/positive', methods=["POST"])
def annote():
    session_id = get_session_id(request)
    with connection_pool.get_connection() as connection:
        user_id = validate_session(connection, session_id)
        if not user_id:
            return jsonify({'error': 'Nem vagy bejelentkezve!'}), 401

    id = request.json['id']

    correct_annotations = {None: '/api/annote/positive', 1: '/api/edit/positive', 0: '/api/change/positive'}
    with connection_pool.get_connection() as connection:
        annotation_label = get_article_annotation(connection, id)
    if request.path != correct_annotations[annotation_label]:
        return jsonify({'error': 'Szerkesztés közben megváltozott a cikk státusza. Kérlek töltsd újra az oldalt!'}), 409

    url = request.json['url']
    title = request.json['title']
    description = request.json['description']
    text = request.json['text']
    persons = request.json['positive_persons']
    institutions = request.json['positive_institutions']
    places = request.json['positive_places']
    others = request.json['tags']
    newspaper_id = request.json['newspaper_id']
    is_active = request.json['active']
    pub_date = request.json['pub_date']
    parsed_date = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
    category = 0
    if 'category' in request.json:
        category = request.json['category']
    file_ids = []
    if 'file_ids' in request.json:
        file_ids = request.json['file_ids']

    with connection_pool.get_connection() as connection:
        if url_exists_in_kmdb(connection, url) and request.path == '/api/annote/positive':
            return jsonify({'error': 'Ez a cikk url alapján már szerepel az adatbázisban. Valószínűleg az autokmdb-n kívülről lett hozzáadva.'}), 409

    with connection_pool.get_connection() as connection:
        annote_positive(connection, id, url, title, title, description, text, persons, institutions, places, newspaper_id, user_id, is_active, category, others, file_ids, parsed_date)
    return jsonify({}), 200


@api.route('/add_url', methods=["POST"])
def add_url():
    session_id = get_session_id(request)
    with connection_pool.get_connection() as connection:
        user_id = validate_session(connection, session_id)
        if not user_id:
            return jsonify({'error': 'Nem vagy bejelentkezve!'}), 401

    with connection_pool.get_connection() as connection:
        url = request.json['url']
        if check_url_exists(connection, url):
            return jsonify({'error': 'Cikk már létezik'}), 400
        init_news(connection, 1, url, url, request.json['newspaper_name'], request.json['newspaper_id'], user_id, None)
        return jsonify({}), 200


@api.route('/all_labels', methods=["GET"])
def all_labels():
    session_id = get_session_id(request)
    with connection_pool.get_connection() as connection:
        if not validate_session(connection, session_id):
            return jsonify({'error': 'Nem vagy bejelentkezve!'}), 401

    with connection_pool.get_connection() as connection:
        return jsonify({
            'person': get_all_persons(connection),
            'institution': get_all_institutions(connection),
            'place': get_all_places(connection),
            'keywords': get_all_others(connection),
            'domains': get_all_newspapers(connection),
            'files': get_all_files(connection),
        }), 200


@api.route('/status')
def hello():
    return 'OK'
