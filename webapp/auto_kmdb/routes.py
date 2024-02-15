from flask import jsonify, Blueprint, request

from auto_kmdb.Article import Article
from auto_kmdb.db import db

api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/articles', methods=["GET"])
def api_articles():
    page = request.args.get('page', 1, type=int)
    pagination = Article.query.filter_by(is_classified=True, is_classified_corruption=True, is_annoted=False).order_by(Article.date.desc()).paginate(page=page, per_page=10)
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
    print(request.json)
    return jsonify({}), 200
