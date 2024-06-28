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
from playwright.async_api import async_playwright


jeti_session = ''
gateway_session = ''
cookies_24 = {}


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


async def main():
    async with async_playwright() as p:
        print('main')

        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://24.hu/")

        await page.wait_for_timeout(1000)

        await page.locator(".css-1tfx6ee").press("Escape")

        await page.get_by_role("link", name="Belépés Regisztráció").click()

        await page.locator("#landing-email").fill(os.environ['USER_24'])

        await page.locator("#btn-next").click()

        await page.wait_for_timeout(1000)

        await page.locator("#password").fill(os.environ['PASS_24'])

        await page.locator("#kc-login").click()

        cookies = await context.cookies()
        cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        await browser.close()
        return cookies_dict


def login_24():
    print('login24')
    cookies_24 = asyncio.run(main())
    print(cookies_24)
    logging.info(cookies_24)


def login_444():
    global jeti_session, gateway_session
    url_1 = 'https://magyarjeti.hu/bejelentkezes?redirect=https%3A%2F%2F444.hu&state=%257B%2522route%2522%253A%2522--reader.index%2522%252C%2522params%2522%253A%255B%255D%257D'
    headers_1 = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://magyarjeti.hu',
        'Connection': 'keep-alive',
        'Referer': 'https://magyarjeti.hu/bejelentkezes?redirect=https%3A%2F%2F444.hu&state=%257B%2522route%2522%253A%2522--reader.index%2522%252C%2522params%2522%253A%255B%255D%257D',
        'Cookie': '_nss=1; PHPSESSID=kr1trgr9ivb20qjf3dkl9h4v54',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'TE': 'trailers',
    }
    data_1 = {
        'username': os.environ['USER_444'],
        'password': os.environ['PASS_444'],
        'send': 'Belépek',
        '_token_': 'gvpg9qzncfeWNlIublxX6T1HXLiT65rfXfRfg=',
        'redirect': 'https://444.hu/',
        'state': '%257B%2522route%2522%253A%2522--reader.index%2522%252C%2522params%2522%253A%255B%255D%257D',
        'list_id': '',
        'callback': '',
        '_do': 'signInForm-submit'
    }

    session = requests.Session()
    session.cookies = requests.cookies.RequestsCookieJar()
    session.post(url_1, headers=headers_1, data=data_1)
    payload = os.environ['PAYL_444']

    url_2 = f'https://gateway.ipa.444.hu/session?payload={payload}%3D%3D&redirect=https%3A%2F%2F444.hu%2F%3Fstate%3D%25257B%252522route%252522%25253A%252522--reader.index%252522%25252C%252522params%252522%25253A%25255B%25255D%25257D'
    headers_2 = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': 'https://magyarjeti.hu/',
        'Connection': 'keep-alive',
        'Cookie': 'abgroup=4;',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'TE': 'trailers',
    }

    session.get(url_2, headers=headers_2)
    cookies = session.cookies
    jeti_session = cookies.get('jeti-session')
    gateway_session = cookies.get('gateway_session')


def get_444(url):
    cookie = f'gateway_session={gateway_session}; jeti-session={jeti_session}'
    logging.info(cookie)
    article_name = url.split('/')[-1]
    date = '-'.join(url.split('/')[-4:-1])
    bucket = '444'
    if url.count('/') == 7:
        bucket = url.split('/')[3]
    response = requests.get(f'https://gateway.ipa.444.hu/api/graphql?crunch=2&operationName=fetchContent&variables=%7B%22slug%22%3A%22{article_name}%22%2C%22date%22%3A%22{date}%22%2C%22buckets%22%3A%5B%22{bucket}%22%5D%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22bb4a4c69fca5577097d0c3f5c9432d5485d8ee2e2e6dfe8f6fbfb61d30e5ed6e%22%7D%7D', headers={'Cookie': cookie})
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
