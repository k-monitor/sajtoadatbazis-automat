import time
import feedparser
from auto_kmdb.options import skip_url_patterns
from auto_kmdb.db import check_url_exists, init_news, connection_pool, get_rss_urls
from auto_kmdb.preprocess import clear_url
import logging
import requests
from datetime import date
from datetime import datetime
from zoneinfo import ZoneInfo


def rss_watcher(app_context):
    logging.info("Started RSS watcher")
    app_context.push()
    with connection_pool.get_connection() as connection:
        newspapers = get_rss_urls(connection)
    while True:
        logging.info("checking feeds")
        for newspaper in newspapers:
            if newspaper["rss_url"]:
                get_new_from_rss(newspaper)
        time.sleep(5 * 60)


def skip_url(url):
    return any(url.startswith(url_pattern) for url_pattern in skip_url_patterns)


def get_new_from_rss(newspaper):
    articles_found = 0
    feed = feedparser.parse(newspaper["rss_url"])

    if newspaper["rss_url"] == "atv":
        logging.info("checking atv")
        response = requests.get(f"https://api.atv.hu/cms/layout-version/published")
        if (
            "generator"
            not in [
                slot
                for slot in response.json()["__boxes__"]
                if slot["name"] == "Itthon"
            ][0]["slotContents"][0]
        ):
            return
        items = [
            slot for slot in response.json()["__boxes__"] if slot["name"] == "Itthon"
        ][0]["slotContents"][0]["generator"]["items"]
        urls_dates = [
            ("https://www.atv.hu/" + article["slug"], article["published_at"])
            for article in items
        ]
        for url, published_at in urls_dates:
            # parsed_date = datetime.strptime(published_at, '%Y-%m-%dT%H:%M:%S.%fZ')
            # pub_time = parsed_date.astimezone(ZoneInfo("Europe/Budapest"))
            clean_url = clear_url(url)
            with connection_pool.get_connection() as connection:
                if not check_url_exists(connection, clean_url) and not skip_url(
                    clean_url
                ):
                    init_news(
                        connection,
                        "rss",
                        url,
                        clean_url,
                        newspaper["name"],
                        newspaper["id"],
                        None,
                        None,
                    )
                    articles_found += 1
    elif newspaper["rss_url"] == "hvg360":
        logging.info("checking hvg360")
        now = date.today().strftime("%Y-%m-%d")
        response = requests.get(
            f"https://hvg.hu/cms-control/latest/{now}?skip=0&limit=20"
        )
        urls_dates = [
            ("https://hvg.hu" + article["url"], article["releaseDateIso"])
            for article in response.json()
            if article["url"].startswith("/360/")
        ]
        for url, release_date in urls_dates:
            # parsed_date = datetime.strptime(release_date, '%Y-%m-%dT%H:%M:%S.%f%z')
            # pub_time = parsed_date.astimezone(ZoneInfo("Europe/Budapest"))
            clean_url = clear_url(url)
            with connection_pool.get_connection() as connection:
                if not check_url_exists(connection, clean_url) and not skip_url(
                    clean_url
                ):
                    init_news(
                        connection,
                        "rss",
                        url,
                        clean_url,
                        newspaper["name"],
                        newspaper["id"],
                        None,
                        None,
                    )
                    articles_found += 1
    else:
        for entry in feed.entries:
            clean_url = clear_url(entry.link)
            pub_time = None
            try:
                parsed_date = datetime.strptime(
                    entry.published, "%a, %d %b %Y %H:%M:%S %z"
                )
                pub_time = parsed_date.astimezone(ZoneInfo("Europe/Budapest"))
            except ValueError:
                if entry.published.endswith("GMT"):
                    parsed_date = datetime.strptime(
                        entry.published, "%a, %d %b %Y %H:%M:%S GMT"
                    )
                    pub_time = parsed_date.astimezone(ZoneInfo("Europe/Budapest"))
                elif entry.published.endswith("Europe/Budapest"):
                    parsed_date = datetime.strptime(
                        entry.published, "%a, %d %b %Y %H:%M:%S Europe/Budapest"
                    )
                    parsed_date = parsed_date.replace(
                        tzinfo=ZoneInfo("Europe/Budapest")
                    )
                    pub_time = parsed_date.astimezone(ZoneInfo("Europe/Budapest"))
                else:
                    logging.warning("No parsing for: " + str(entry.published))
            except Exception:
                pub_time = None
            with connection_pool.get_connection() as connection:
                if not check_url_exists(connection, clean_url) and not skip_url(
                    clean_url
                ):
                    init_news(
                        connection,
                        "rss",
                        entry.link,
                        clean_url,
                        newspaper["name"],
                        newspaper["id"],
                        None,
                        pub_time,
                    )
                    articles_found += 1

    if articles_found > 0:
        logging.info(newspaper["name"] + " found " + str(articles_found) + " articles")
