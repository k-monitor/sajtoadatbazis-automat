import time
import traceback

import requests

from auto_kmdb.Article import Article
from auto_kmdb.db import db
import jsonlines

CLASSIFICATION_SERVER = 'http://bert_api:8000'
KEYWORD_GENERATION_SERVER = 'http://keyword_extraction:8000'
PEOPLE_INSTITUTIONS_SERVER = 'http://entity_extraction:8000'
SPACY_SERVER = 'http://spacy_api:8000'
RELATION_EXTRACTION_SERVER = 'http://relation_extraction:8000'

article_classification_prompt = '''{title}
{description}'''
keyword_generation_prompt = '''[címkék generálása]
{title}

{description}

{text}

cimkék: {keywords}

###

korrupciós címkék:'''
people_classification_prompt = '''[személy klasszifikáció]
{text}

###

összes: {all}
korrupcióban érintett:'''
institution_classification_prompt = '''[intézmény klasszifikáció]
{text}

###

összes: {all}
korrupcióban érintett:'''
relation_extraction_prompt = '''Bekezdés:
"{text}"

Relációk:
'''


def parse_relations(output):
    if output == 'Nincs kapcsolat.':
        return []
    relations = []
    for section in output.split('\n\n'):
        lines = section.split('\n')
        if len(lines) != 4:
            return None
        if not (lines[0].startswith('Indoklás: ') or
                lines[1].startswith('Kapcsolat: ') or
                lines[2].startswith('Tárgy: ') or
                lines[3].startswith('Alany: ')):
            return None
        relations.append({
            "explanation": lines[0].replace('Indoklás: ', '').replace('"', ''),
            "relation": lines[1].replace('Kapcsolat: ', '').replace('"', ''),
            "subject": lines[2].replace('Tárgy: ', '').replace('"', ''),
            "object": lines[3].replace('Alany: ', '').replace('"', ''),
        })
    return relations


def article_processor(appcontext):
    appcontext.push()
    while True:
        query = Article.query.filter_by(is_classified=False)
        while query.count() > 0:
            article = query.first()
            process(article, do_classification)
            db.session.commit()
            if article.is_classified_corruption:
                for fun in [do_keyword_generation, do_spacy_entities, do_people_classification, do_institution_classification, do_relation_extraction]:
                    process(article, fun)
                    db.session.commit()
        time.sleep(1*60)


def do_classification(article: Article):
    text = article_classification_prompt.format(title=article.title,
            description=article.description, text=article.text,
            keywords=', '.join(article.keywords))
    resp = requests.post(CLASSIFICATION_SERVER+'/classify',
                                 json={"text": text}, timeout=1800)
    respText = resp.json()['class']
    print(respText)
    if respText == 'corruption':
        print('found corruption', article.title)
        article.is_classified_corruption = True
    article.is_classified = True


def do_spacy_entities(article: Article):
    resp = requests.post(SPACY_SERVER+'/entities',
                                 json={"text": article.text}, timeout=1800)
    respText = resp.json()
    print(respText)
    article.people = respText['people']
    article.institutions = respText['institutions']


def do_keyword_generation(article: Article):
    text = keyword_generation_prompt.format(title=article.title,
            description=article.description, text=article.text,
            keywords=', '.join(article.keywords))

    resp = requests.post(KEYWORD_GENERATION_SERVER+'/completion',
                                 json={"prompt": text}, timeout=1800)
    respText = resp.json()['content'].strip()
    print(respText)
    article.tags = respText


def do_people_classification(article: Article):
    text = people_classification_prompt.format(text=article.text,
                                               all=article.people)

    resp = requests.post(PEOPLE_INSTITUTIONS_SERVER+'/completion',
                                 json={"prompt": text}, timeout=1800)
    respText = resp.json()['content'].strip()
    print(respText)
    article.corrupt_people = respText


def do_institution_classification(article: Article):
    text = institution_classification_prompt.format(text=article.text,
                                                    all=article.institutions)

    resp = requests.post(PEOPLE_INSTITUTIONS_SERVER+'/completion',
                                 json={"prompt": text}, timeout=1800)
    respText = resp.json()['content'].strip()
    print(respText)
    article.corrupt_institutions = respText


def do_relation_extraction(article: Article):
    relations = []
    for paragraph in article.text.split('\n'):
        text = relation_extraction_prompt.format(text=paragraph.replace('"', "'"))
        resp = requests.post(RELATION_EXTRACTION_SERVER+'/completion',
                             json={"prompt": text}, timeout=1800)
        respText = resp.json()['content'].strip()
        print(respText)
        relations += parse_relations(respText)
    print(relations)
    with jsonlines.open(f'/data/relation_extraction.jsonl', mode='a') as writer:
        writer.write_all(relations)


def process(article: Article, f):
    print('processing url:', article.url)
    retry = 0
    while True:
        retry += 1
        if retry >= 10:
            print('max retry reached')
            break
        try:
            t = time.time()
            print('sending request to local server')
            f(article)
            elapsed_time = time.time() - t
            print('done in:', elapsed_time)
            break
        except Exception:
            traceback.print_exc()
            print('exception occured, retrying in 10 seconds')
            time.sleep(10)

