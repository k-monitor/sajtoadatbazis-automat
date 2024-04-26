from bs4 import BeautifulSoup
import jsonlines

from datasets import load_dataset

dataset = load_dataset("boapps/kmdb_bert_entities")['train']

tid = dict()
with jsonlines.open('texts.jsonl') as reader, jsonlines.open('ftexts.jsonl', 'w') as writer:
    for n in reader:
        if not n['text']:
            continue
        s = BeautifulSoup(n['text'], 'html.parser')
        n['text'] = '\n'.join([t.text for t in s.find_all('p')])
        writer.write(n)
        tid[n['news_id']] = n['text']

cid = dict()
with jsonlines.open('cats_and_places.jsonl') as reader, jsonlines.open('cats_texts.jsonl', 'w') as writer:
    for n in reader:
        if n['news_id'] not in tid:
            continue
        n['text'] = tid[n['news_id']]
        writer.write(n)
        cid[n['news_id']] = n['cat']

dataset = dataset.filter(lambda row: row['id'] in cid)
dataset = dataset.map(lambda row: {'category': cid[row['id']]})
dataset = dataset.remove_columns(['people', 'institutions', 'places', 'ent_lemmas', 'ent_tokens', 'words', 'classifications'])
dataset = dataset.filter(lambda row: row['category'] in ['magyar-hirek', 'eu-hirek', 'vilag-hirek'])
dataset = dataset.map(lambda row: {'category':  {'magyar-hirek':0, 'eu-hirek':1, 'vilag-hirek':2}[row['category']]})

dataset.to_json('catds.jsonl')
