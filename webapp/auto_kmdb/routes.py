from flask import jsonify, Blueprint, request

from auto_kmdb.Article import Article
from auto_kmdb.db import db

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
    db.session.commit()
    return jsonify({}), 200

@api.route('/add_url', methods=["POST"])
def add_url():
    print(request.json['url'])
    return jsonify({}), 200

@api.route('/all_labels', methods=["GET"])
def all_labels():
    return jsonify({
        'person': ['Mészáros Lőrinc', 'Orbán Viktor', 'Gyurcsány Ferenc'],
        'institution': ['Fidesz', 'MSZP', 'BKV (Budapesti Közlekedési Vállalat) Zrt.'],
        'place': ['Budapest', 'Európa', 'Pest megye'],
        'keywords': ['klientúra', 'ingatlan', 'közbeszerzés'],
        'domains': ['mind', 'telex.hu', 'hvg.hu', '444.hu'],
    }), 200
