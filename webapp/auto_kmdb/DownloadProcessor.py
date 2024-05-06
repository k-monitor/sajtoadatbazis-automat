from auto_kmdb.Processor import Processor
from auto_kmdb.same_news import same_news
from auto_kmdb.db import get_download_queue, save_download_step, skip_same_news, skip_download_error
from auto_kmdb.preprocess import do_replacements, replacements, common_descriptions
from time import sleep
import newspaper
from auto_kmdb.db import connection_pool
import os
import requests
from bs4 import BeautifulSoup


class DownloadProcessor(Processor):
    def __init__(self):
        pass
        # super().__init__()

    def process_next(self):
        with connection_pool.get_connection() as connection:
            next_row = get_download_queue(connection)
        print('Downloading')
        if next_row is None:
            sleep(30)
            return

        print('Downloading', next_row['url'])
        try:
            article = newspaper.article(next_row['url'])
        except Exception as e:
            print(e)
            with connection_pool.get_connection() as connection:
                skip_download_error(connection, next_row['id'])
            return

        text = article.text
        title = article.title

        if 'Csatlakozz a Körhöz, és olvass tovább!' in article.text:
            text = self.get_444(next_row['url'].split('/')[-1].split('?')[0])
        elif 'hvg.hu/360/' in next_row['url']:
            text += '\n'+self.get_hvg(next_row['url'].split('/360/')[1].split('?')[0])

        title = do_replacements(title, replacements)
        text = do_replacements(text, replacements)

        authors = ','.join([a for a in article.authors if ' ' in a])

        description = article.meta_description
        for common_description in common_descriptions:
            description = description.replace(common_description.strip(), '')

        if len(description) < 1 and text.count('\n') > 1:
            sl = text.splitlines()[0]
            description = sl[:sl[:400].rfind('.')+1]
            if '.' not in sl[:400]:
                description = sl[:400]

        date = article.publish_date

        if same_news(title, description, text) and next_row['source'] != 1:
            with connection_pool.get_connection() as connection:
                skip_same_news(connection, next_row['id'], text, title, description, authors, date)
        else:
            with connection_pool.get_connection() as connection:
                save_download_step(connection, next_row['id'], text, title, description, authors, date)

    def get_444(self, article_name):
        cookie = os.environ["COOKIE_444"]
        response = requests.get(f'https://gateway.ipa.444.hu/api/graphql?crunch=2&operationName=fetchContent&variables=%7B%22slug%22%3A%22{article_name}%22%2C%22date%22%3A%222024-04-26%22%2C%22buckets%22%3A%5B%22444%22%5D%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22bb4a4c69fca5577097d0c3f5c9432d5485d8ee2e2e6dfe8f6fbfb61d30e5ed6e%22%7D%7D', headers={'Cookie': cookie})
        text = '\n'.join([BeautifulSoup(f['content'], features="lxml").text for f in response.json()['data']['crunched'][-1]['content']['body'][0] if isinstance(f, dict) and 'content' in f])
        return text

    def get_hvg(self, webid):
        token = os.environ["TOKEN_HVG"]
        premium_html = requests.get(f'https://api.hvg.hu/web//articles/premiumcontent/?webid={webid}&apiKey=4f67ed9596ac4b11a4b2ac413e7511af', headers={'Authorization': 'Bearer '+token}).content
        soup = BeautifulSoup(premium_html, features="lxml")
        premium_text = '\n'.join([t.text for t in soup.find_all('p')])
        premium_text = premium_text.replace('A hvg360 tartalma, így a fenti cikk is, olyan érték, ami nem jöhetett volna létre a te előfizetésed nélkül. Ha tetszett az írásunk, akkor oszd meg a minőségi újságírás élményét szeretteiddel is, és ajándékozz hvg360-előfizetést!', '')
        return premium_text
