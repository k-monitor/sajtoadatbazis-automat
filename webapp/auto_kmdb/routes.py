from flask import jsonify, Blueprint, request
from auto_kmdb.db import get_articles, annote_negative, connection_pool
from auto_kmdb.db import get_all_persons, get_all_institutions, get_all_places, get_all_others, get_all_newspapers
from auto_kmdb.db import check_url_exists, init_news, 
from math import ceil
import json

api = Blueprint('api', __name__, url_prefix='/api')


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


@api.route('/articles', methods=["GET"])
def api_articles():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'mixed', type=str)
    domain = request.args.get('domain', 'mind', type=str)

    with connection_pool.get_connection() as connection:
        length, articles = get_articles(connection, page, status, domain)
        articles = [reformat_article(a) for a in articles]

        return jsonify({'pages': ceil(length/10), 'articles': articles}), 200


@api.route('/annote/negative', methods=["POST"])
def not_corruption():
    id = request.json['id']
    with connection_pool.get_connection() as connection:
        annote_negative(connection, id)
        return jsonify({}), 200


@api.route('/annote/positive', methods=["POST"])
def annote():
    id = request.json['id']
    # TODO

    return jsonify({}), 200


@api.route('/add_url', methods=["POST"])
def add_url():
    with connection_pool.get_connection() as connection:
        url = request.json['url']
        if check_url_exists(connection, url):
            return jsonify({'error': 'Cikk már létezik'}), 400
        init_news(connection, 1, url, url)
        return jsonify({}), 200


@api.route('/all_labels', methods=["GET"])
def all_labels():
    with connection_pool.get_connection() as connection:
        return jsonify({
            'person': get_all_persons(connection),
            'institution': get_all_institutions(connection),
            'place': get_all_places(connection),
            'keywords': get_all_others(connection),
            'domains': get_all_newspapers(connection),
        }), 200


@api.route('/status')
def hello():
    return 'OK'
