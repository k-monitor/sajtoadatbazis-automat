import time
import traceback

import feedparser
import newspaper

from auto_kmdb.Article import Article
from auto_kmdb.options import feed_urls, skip_url_patterns
from auto_kmdb.db import db
from auto_kmdb.same_news import same_news


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
        if Article.query.filter_by(original_url=entry.link).count() == 0:
            if any(entry.link.startswith(url_pattern) for url_pattern in skip_url_patterns):
                articles_skipped += 1
                continue
            try:
                article = Article(entry.link)
                if same_news(article):
                    print('found same:', entry.link)
                    continue
                db.session.add(article)
                articles_found += 1
                db.session.commit()
                print('article added:', entry.link)
            except newspaper.ArticleException:
                traceback.print_exc()
            finally:
                time.sleep(3)
    if articles_found > 0:
        print(url, 'found', articles_found, 'articles')
    if articles_skipped > 0:
        print(url, 'skipped', articles_skipped, 'articles')
