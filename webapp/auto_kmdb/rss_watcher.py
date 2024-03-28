import time
import feedparser
from auto_kmdb.options import skip_url_patterns
from auto_kmdb.db import check_url_exists, init_news, connection_pool, get_rss_urls
from auto_kmdb.preprocess import clear_url


connection = connection_pool.get_connection()
# TODO erre szebb megoldas, talan classba szervezes


def rss_watcher(app_context):
    app_context.push()
    newspapers = get_rss_urls(connection)
    while True:
        print('checking feeds')
        for newspaper in newspapers:
            if newspaper['rss_url']:
                get_new_from_rss(newspaper)
        time.sleep(5*60)


def get_new_from_rss(newspaper):
    articles_found = 0
    articles_skipped = 0
    feed = feedparser.parse(newspaper['rss_url'])
    for entry in feed.entries:
        clean_url = clear_url(entry.link)
        if not check_url_exists(connection, clean_url):
            if any(entry.link.startswith(url_pattern) for url_pattern in skip_url_patterns):
                articles_skipped += 1
                continue
            init_news(connection, 'rss', entry.link, clean_url, newspaper['name'], newspaper['id'])
            articles_found += 1
    if articles_found > 0:
        print(newspaper['name'], 'found', articles_found, 'articles')
    if articles_skipped > 0:
        print(newspaper['name'], 'skipped', articles_skipped, 'articles')
