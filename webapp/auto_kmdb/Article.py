import re
from urllib.parse import urlparse

from auto_kmdb.db import db


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __init__(self, name):
        self.name = name


article_tag = db.Table('article_tag',
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String)
    original_url = db.Column(db.String)
    title = db.Column(db.String)
    text = db.Column(db.String)
    description = db.Column(db.String)
    date = db.Column(db.String)
    tags = db.Column(db.String)
    people = db.Column(db.String)
    institutions = db.Column(db.String)
    corrupt_people = db.Column(db.String)
    corrupt_institutions = db.Column(db.String)
    keywords = db.relationship('Tag', secondary=article_tag, backref=db.backref('articles', lazy='dynamic'))

    is_classified = db.Column(db.Boolean, default=False)
    is_classified_corruption = db.Column(db.Boolean, default=False)
    classification_score = db.Column(db.Integer, default=0)

    is_annoted = db.Column(db.Boolean, default=False)
    is_annoted_corruption = db.Column(db.Boolean, default=True)

    def __init__(self, url: str):
        import newspaper

        self.original_url = url
        self.url: str = clear_url(url)

        self.news_article = newspaper.Article(self.url)
        self.download()
        self.parse()

        self.prepare_title()
        self.prepare_text()
        self.prepare_description()
        self.prepare_keywords()
        self.prepare_date()

        self.text = do_replacements(self.text, replacements).strip()
        self.description = do_replacements(self.description, replacements).strip()
        self.title = do_replacements(self.title, replacements).strip()

    def download(self):
        self.news_article.download()

    def parse(self):
        self.news_article.parse()

    def prepare_title(self):
        self.title: str = self.news_article.title
        self.title = do_replacements(self.title, replacements)

    def prepare_text(self):
        self.text: str = self.news_article.text+'\n'
        self.text = do_replacements(self.text, replacements)
        for line in common_lines:
            if line in self.text:
                self.text = self.text.replace('\n'+line, '\n')

    def prepare_description(self):
        self.description = self.news_article.meta_description
        self.description = do_replacements(self.description, replacements)

        for description in common_descriptions:
            self.description = self.description.replace(description.strip(), '')

        if len(self.description) < 1 and self.text.count('\n') > 1:
            sl = self.text.splitlines()[0]
            self.description = sl[:sl[:400].rfind('.')+1]
            if '.' not in sl[:400]:
                self.description = sl[:400]

    def prepare_keywords(self):
        self.keywords = self.news_article.keywords

    def prepare_date(self):
        self.date = self.news_article.publish_date
        if self.date is not None:
            self.date = self.date.strftime('%Y. %m. %d. %H:%M:%S')
        else:
            self.date = ''

    def __str__(self):
        return str(self.dict())

    def __repr__(self):
        return self.__str__()

    def dict(self):
        return {
            'id': self.id,
            'classification_score': self.classification_score,
            'url': self.url,
            'title': self.title,
            'text': self.text,
            'description': self.description,
            'keywords': self.keywords,
            'tags': self.tags.split(', ') if self.tags else [],
            'people': self.people.split(', ') if self.people else [],
            'institutions': self.institutions.split(', ') if self.institutions else [],
            'places': [],
            'corrupt_people': self.corrupt_people.split(', ') if self.corrupt_people else [],
            'corrupt_institutions': self.corrupt_institutions.split(', ') if self.corrupt_institutions else [],
            'corrupt_places': [],
            'is_annoted': self.is_annoted,
            'is_annoted_corruption': self.is_annoted_corruption,
            'is_classified': self.is_classified,
            'is_classified_corruption': self.is_classified_corruption,
            'date': self.date,
        }
