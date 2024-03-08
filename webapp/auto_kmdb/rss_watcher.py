import time
import traceback

import feedparser
from auto_kmdb.options import feed_urls, skip_url_patterns
from auto_kmdb.db import check_url_exists, init_news
from auto_kmdb.preprocess import clear_url


def rss_watcher(app_context):
    app_context.push()
    while True:
        for feed_url in feed_urls:
            get_new_from_rss(feed_url)
        time.sleep(5*60)


def get_new_from_rss(url):
    articles_found = 0
    articles_skipped = 0
    feed = feedparser.parse(url)
    for entry in feed.entries:
        clean_url = clear_url(entry.link)
        if check_url_exists(clean_url):
            if any(entry.link.startswith(url_pattern) for url_pattern in skip_url_patterns):
                articles_skipped += 1
                continue
            init_news('rss', entry.link, clean_url)
            articles_found += 1
            print('article added:', entry.link)
    if articles_found > 0:
        print(url, 'found', articles_found, 'articles')
    if articles_skipped > 0:
        print(url, 'skipped', articles_skipped, 'articles')
