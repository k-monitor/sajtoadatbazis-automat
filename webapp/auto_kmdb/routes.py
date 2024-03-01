from flask import jsonify, Blueprint, request

from auto_kmdb.Article import Article
from auto_kmdb.db import db
from auto_kmdb.db import get_all_persons, get_all_institutions, get_all_places, get_all_others, get_all_newspapers


api = Blueprint('api', __name__, url_prefix='/api')


@api.route('/articles', methods=["GET"])
def api_articles():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'mixed', type=str)
    domain = request.args.get('domain', 'mind', type=str)
    query = None
    if status == 'mixed':
        query = Article.query.filter_by(is_classified=True, is_classified_corruption=True, is_annoted=False)
    elif status == 'positive':
        query = Article.query.filter_by(is_classified=True, is_annoted_corruption=True, is_annoted=True)
    else:
        query = Article.query.filter_by(is_classified=True, is_annoted_corruption=False, is_annoted=True)
    if domain != 'mind':
        query = query.filter(Article.url.contains(domain))
    pagination = query.order_by(Article.date.desc()).paginate(page=page, per_page=10)
    return jsonify({'pages': pagination.pages, 'articles': [a.dict() for a in pagination]}), 200

@api.route('/not_corruption', methods=["POST"])
def not_corruption():
    id = request.json['id']
    Article.query.filter_by(id=id).first().is_annoted = True
    Article.query.filter_by(id=id).first().is_annoted_corruption = False
    db.session.commit()
    return jsonify({}), 200


@api.route('/annote', methods=["POST"])
def annote():
    id = request.json['id']
    Article.query.filter_by(id=id).first().is_annoted = True
    Article.query.filter_by(id=id).first().is_annoted_corruption = True
    Article.query.filter_by(id=id).first().title = request.json['title']
    Article.query.filter_by(id=id).first().url = request.json['url']
    Article.query.filter_by(id=id).first().description = request.json['description']
    Article.query.filter_by(id=id).first().text = request.json['text']
    # Article.query.filter_by(id=id).first().keywords = ', '.join(request.json['keywords'])
    Article.query.filter_by(id=id).first().tags = request.json['tags']
    # Article.query.filter_by(id=id).first().people = ', '.join(request.json['people'])
    # Article.query.filter_by(id=id).first().institutions = ', '.join(request.json['institutions'])
    # Article.query.filter_by(id=id).first().places = ', '.join(request.json['places'])
    Article.query.filter_by(id=id).first().corrupt_people = ', '.join(request.json['corrupt_people'])
    Article.query.filter_by(id=id).first().corrupt_institutions = ', '.join(request.json['corrupt_institutions'])
    Article.query.filter_by(id=id).first().corrupt_places = ', '.join(request.json['corrupt_places'])
    db.session.commit()
    return jsonify({}), 200


@api.route('/add_url', methods=["POST"])
def add_url():
    print(request.json['url'])
    if Article.query.filter_by(url=request.json['url']).first() is not None:
        return jsonify({'error': 'Cikk már létezik'}), 400
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
