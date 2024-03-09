from flask import jsonify, Blueprint, request
from auto_kmdb.db import get_articles, annote_negative
from auto_kmdb.db import get_all_persons, get_all_institutions, get_all_places, get_all_others, get_all_newspapers
from auto_kmdb.db import check_url_exists, init_news
from math import ceil

api = Blueprint('api', __name__, url_prefix='/api')


@api.route('/articles', methods=["GET"])
def api_articles():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'mixed', type=str)
    domain = request.args.get('domain', 'mind', type=str)

    length, articles = get_articles(page, status, domain)

    return jsonify({'pages': ceil(length/10), 'articles': articles}), 200


@api.route('/not_corruption', methods=["POST"])
def not_corruption():
    id = request.json['id']
    annote_negative(id)
    return jsonify({}), 200


@api.route('/annote', methods=["POST"])
def annote():
    id = request.json['id']
    # TODO
    return jsonify({}), 200


@api.route('/add_url', methods=["POST"])
def add_url():
    url = request.json['url']
    if check_url_exists(url):
        return jsonify({'error': 'Cikk már létezik'}), 400
    init_news(1, url, url)
    return jsonify({}), 200


@api.route('/all_labels', methods=["GET"])
def all_labels():
    return jsonify({
        'person': get_all_persons(),
        'institution': get_all_institutions(),
        'place': get_all_places(),
        'keywords': get_all_others(),
        'domains': get_all_newspapers(),
    }), 200
