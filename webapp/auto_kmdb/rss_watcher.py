import re
from typing import Any, Optional
import feedparser
from auto_kmdb import db
from auto_kmdb.utils.preprocess import clear_url
import logging
import requests
from datetime import date
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
import cloudscraper


scraper = cloudscraper.create_scraper(browser="chrome")
proxy_host: str = os.environ["MYSQL_HOST"]
request_proxies: dict[str, str] = {
    "http": "socks5h://" + proxy_host + ":1080",
    "https": "socks5h://" + proxy_host + ":1080",
}
scraper.proxies.update(request_proxies)


def load_json_from_file(filename: str) -> dict:
    with open(filename) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


skip_url_patterns = load_json_from_file("data/skip_url_patterns.json")


def rss_watcher(app_context):
    logging.info("Started RSS watcher")
    app_context.push()
    with db.connection_pool.get_connection() as connection:
        newspapers: list[dict] = db.get_rss_urls(connection)
    while True:
        logging.info("checking feeds")
        for newspaper in newspapers:
            if newspaper["rss_url"]:
                try:
                    get_new_from_rss(newspaper)
                except requests.exceptions.JSONDecodeError:
                    logging.error("JSONDecodeError for " + newspaper["name"])
                except Exception as e:
                    logging.error("Error for " + newspaper["name"] + ": " + str(e))
        logging.info("done checking feeds")


def skip_url(url) -> bool:
    return any(url.startswith(url_pattern) for url_pattern in skip_url_patterns)


def get_atv():
    logging.info("checking atv")
    response: requests.Response = scraper.get(
        f"https://api.atv.hu/cms/layout-version/published"
    )
    if (
        "generator"
        not in [
            slot for slot in response.json()["__boxes__"] if slot["name"] == "Itthon"
        ][0]["slotContents"][0]
    ):
        return []
    items: list[dict] = [
        slot for slot in response.json()["__boxes__"] if slot["name"] == "Itthon"
    ][0]["slotContents"][0]["generator"]["items"]
    urls_dates = [
        ("https://www.atv.hu/" + article["slug"], article["published_at"])
        for article in items
    ]
    return urls_dates


def get_hvg360():
    logging.info("checking hvg360")
    now: str = date.today().strftime("%Y-%m-%d")
    response = requests.get(f"https://hvg.hu/cms-control/latest/{now}?skip=0&limit=20")

    urls_dates = [
        ("https://hvg.hu" + article["url"], article["releaseDateIso"])
        for article in response.json()
        if article["url"].startswith("/360/")
    ]
    return urls_dates


def get_rss(rssurl):
    try:
        response = scraper.get(rssurl)
        feed = feedparser.parse(response.content)
    except Exception as e:
        logging.error(f"Error fetching RSS feed {rssurl}: {str(e)}")
        return []

    urls_dates = []
    for entry in feed.entries:
        clean_url = clear_url(entry.link)
        pub_time: Optional[datetime] = None
        try:
            parsed_date: datetime = datetime.strptime(
                entry.published, "%a, %d %b %Y %H:%M:%S %z"
            )
            pub_time = parsed_date.astimezone(ZoneInfo("Europe/Budapest"))
        except ValueError:
            try:
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
                    # NEW: Handle ISO 8601 format (e.g., "2025-01-29T13:41:38.414+01:00")
                    parsed_date = datetime.fromisoformat(entry.published)
                    pub_time = parsed_date.astimezone(ZoneInfo("Europe/Budapest"))

            except ValueError:
                logging.warning("No parsing for: " + str(entry.published))
                pub_time = None

        except Exception:
            pub_time = None

        urls_dates.append((clean_url, pub_time))

    return urls_dates


def get_new_from_rss(newspaper):
    articles_found = 0

    urls_dates: list[tuple[str, Optional[str]]] = []
    if newspaper["rss_url"] == "atv":
        urls_dates = get_atv()
    elif newspaper["rss_url"] == "hvg360":
        urls_dates = get_hvg360()
    else:
        urls_dates = get_rss(newspaper["rss_url"])
    for url, release_date in urls_dates:
        # parsed_date = datetime.strptime(release_date, '%Y-%m-%dT%H:%M:%S.%f%z')
        # pub_time = parsed_date.astimezone(ZoneInfo("Europe/Budapest"))
        clean_url: str = clear_url(url)
        with db.connection_pool.get_connection() as connection:
            if not db.check_url_exists(connection, clean_url) and not skip_url(
                clean_url
            ) and not re.fullmatch(r'.*\/\d{4}\/\d{2}', clean_url):
                db.init_news(
                    connection,
                    "rss",
                    url,
                    clean_url,
                    newspaper["name"],
                    newspaper["id"],
                    1,
                    release_date,
                )
                articles_found += 1

    if articles_found > 0:
        logging.info(newspaper["name"] + " found " + str(articles_found) + " articles")
