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
import logging
from auto_kmdb.db import get_retries_from
from datetime import datetime, timedelta
import asyncio
from playwright.sync_api import sync_playwright


jeti_session = ''
gateway_session = ''
cookies_24 = {}
cookies_444 = {}


def process_article(id, url, source):
    try:
        headers = {'User-Agent': 'autokmdb'}
        response = requests.get(url, headers=headers, cookies=cookies_24)
        article = newspaper.Article(url=url)
        article.download(input_html=response.content)
        article.parse()
    except Exception as e:
        logging.error(e)
        with connection_pool.get_connection() as connection:
            skip_download_error(connection, id)
        return

    text = article.text
    title = article.title
    is_paywalled = 0

    if 'Csatlakozz a Körhöz, és olvass tovább!' in article.html:
        text = get_444(url.split('?')[0])
        is_paywalled = 1
    elif 'hvg.hu/360/' in url:
        text += '\n'+get_hvg(url.split('/360/')[1].split('?')[0])
        is_paywalled = 1

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

    if same_news(title, description, text) and source != 1:
        with connection_pool.get_connection() as connection:
            skip_same_news(connection, id, text, title, description, authors, date, is_paywalled)
    else:
        with connection_pool.get_connection() as connection:
            save_download_step(connection, id, text, title, description, authors, date, is_paywalled)


def login_24():
    global cookies_24
    username = os.environ['USER_24']
    password = os.environ['PASS_24']
    with sync_playwright() as p:    
        browser = p.firefox.launch()
        context = browser.new_context()        
        page = context.new_page()

        page.goto("https://24.hu/")
        page.locator(".css-1tfx6ee").press("Escape")

        page.get_by_role("link", name="Belépés Regisztráció").click()

        page.locator("#landing-email").fill(username)
        page.locator("#btn-next").click()

        page.wait_for_timeout(1000)

        page.locator("#password").fill(password)
        page.locator("#kc-login").click()

        cookies = context.cookies()
        cookies_24 = {cookie['name']: cookie['value'] for cookie in cookies}

        browser.close()

    logging.info(cookies_24)


def login_444():
    global cookies_444
    username = os.environ['USER_444']
    password = os.environ['PASS_444']
    with sync_playwright() as p:
        browser = p.firefox.launch()
        context = browser.new_context()
        page = context.new_page()
        page.goto("http://444.hu")

        page.wait_for_timeout(1000)

        def handler():
            page.get_by_role("button", name="ELFOGADOM", exact=True).click()

        page.add_locator_handler(page.get_by_role("button", name="ELFOGADOM", exact=True), handler)

        page.get_by_title("Felhasználói fiók").click()
        page.screenshot(path="screenshot.png")

        page.get_by_role("button", name="Bejelentkezés", exact=False).click()  
        page.wait_for_timeout(1000)

        page.add_locator_handler(page.get_by_role("button", name="ELFOGADOM", exact=True), handler)

        page.locator("#frm-signInForm-username").fill(username)
        page.locator("#frm-signInForm-password").fill(password)
        page.wait_for_timeout(1000)

        page.locator(".md-filled-button-profile").click()
        page.wait_for_timeout(1000)

        cookies = context.cookies()
        cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}    

        browser.close()

        cookies_444 = cookies_dict


def get_444(url):
    article_name = url.split('/')[-1]
    date = '-'.join(url.split('/')[-4:-1])
    bucket = '444'
    if url.count('/') == 7:
        bucket = url.split('/')[3]

    response = requests.get(f'https://gateway.ipa.444.hu/api/graphql?crunch=2&operationName=fetchContent&variables=%7B%22onlyReports%22%3Afalse%2C%22order%22%3A%22DESC%22%2C%22slug%22%3A%22{article_name}%22%2C%22date%22%3A%22{date}%22%2C%22buckets%22%3A%5B%22{bucket}%22%5D%2C%22cursorInclusive%22%3Afalse%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22376c5324c94249caa29a66aeb02f8ed7c593ce2d9036098f1ba63a545405c96a%22%7D%7D', cookies=cookies_444)
    text = '\n'.join([BeautifulSoup(f['content'], features="lxml").text for f in response.json()['data']['crunched'][-1]['content']['body'][0] if isinstance(f, dict) and 'content' in f])
    return text


def get_hvg(webid):
    token = os.environ["TOKEN_HVG"]
    premium_html = requests.get(f'https://api.hvg.hu/web//articles/premiumcontent/?webid={webid}&apiKey=4f67ed9596ac4b11a4b2ac413e7511af', headers={'Authorization': 'Bearer '+token}).content
    soup = BeautifulSoup(premium_html, features="lxml")
    premium_text = '\n'.join([t.text for t in soup.find_all('p')])
    premium_text = premium_text.replace('A hvg360 tartalma, így a fenti cikk is, olyan érték, ami nem jöhetett volna létre a te előfizetésed nélkül. Ha tetszett az írásunk, akkor oszd meg a minőségi újságírás élményét szeretteiddel is, és ajándékozz hvg360-előfizetést!', '')
    return premium_text


def do_retries(app_context):
    app_context.push()

    current_date = datetime.now()
    new_date = current_date - timedelta(days=3)
    formatted_date = new_date.strftime("%Y-%m-%d")

    with connection_pool.get_connection() as connection:
        rows = get_retries_from(connection, formatted_date)
    for row in rows:
        logging.info('retrying: ' + row['url'])
        process_article(row['id'], row['url'], row['source'])
        sleep(3)


class DownloadProcessor(Processor):
    def __init__(self):
        logging.info('initialized download processor')
        pass
        # super().__init__()

    def process_next(self):
        with connection_pool.get_connection() as connection:
            next_row = get_download_queue(connection)
        if next_row is None:
            sleep(30)
            return
        logging.info('download processor is processing: ' + next_row['url'])
        process_article(next_row['id'], next_row['url'], next_row['source'])
