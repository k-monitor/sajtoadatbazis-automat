from multiprocessing import process
from typing import NamedTuple, List, Optional

from flask.ctx import AppContext
from playwright._impl._api_structures import Cookie
from playwright.sync_api._generated import Browser, BrowserContext, Page
from auto_kmdb.processors import Processor
from auto_kmdb.utils.same_news import same_news
from auto_kmdb import db
from auto_kmdb.utils.preprocess import (
    do_replacements,
    replacements,
    common_descriptions,
    trim_title,
)
from time import sleep
import newspaper
import os
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from auto_kmdb.newspapers.Telex import Telex
from auto_kmdb.newspapers.Atv import Atv
from auto_kmdb.newspapers.Mediaworks import Mediaworks
from auto_kmdb.newspapers.Hvg import Hvg
from auto_kmdb.newspapers.Propeller import Propeller
from datetime import timezone
import traceback
from auto_kmdb.newspapers.Newspaper import Newspaper
import cloudscraper


scraper = cloudscraper.create_scraper(browser="chrome")


class ArticleDownload(NamedTuple):
    text: str
    title: str
    description: str
    authors: str
    date: Optional[datetime]
    is_paywalled: int
    same_news_id: Optional[int]


newspapers: list[Newspaper] = [Telex(), Atv(), Mediaworks(), Hvg(), Propeller()]
proxy_host: str = os.environ["MYSQL_HOST"]
request_proxies: dict[str, str] = {
    "http": "socks5h://" + proxy_host + ":1080",
    "https": "socks5h://" + proxy_host + ":1080",
}
newspaper_config = newspaper.configuration.Configuration()
newspaper_config.update(fetch_images=False)
scraper.proxies.update(request_proxies)
playwright_proxy = {"server": "socks5://" + proxy_host + ":1080"}


def get_custom_text(url: str, html: str) -> Optional[str]:
    for paper in newspapers:
        if paper.is_url_this(url, html):
            return paper.get_text(url, html)


def get_custom_description(url: str, html: str) -> Optional[str]:
    for paper in newspapers:
        if paper.is_url_this(url, html):
            return paper.get_description(url, html)


def get_custom_title(url: str, html: str) -> Optional[str]:
    for paper in newspapers:
        if paper.is_url_this(url, html):
            return paper.get_title(url, html)


def get_html(url: str, cookies: dict[str, str]) -> str:
    headers: dict[str, str] = {"User-Agent": "autokmdb"}
    response: requests.Response = scraper.get(url, headers=headers, cookies=cookies)
    if response.status_code >= 400:
        raise Exception(
            "Got error while downloading article.",
            response.status_code,
            url,
            response.headers,
        )
    return str(response.text)


def process_article(
    url: str, html: str, cookies: dict[str, str], skip_paywalled=False
) -> ArticleDownload:
    article = newspaper.Article(url=url, config=newspaper_config)
    article.download(
        input_html=html.replace("<br>", "\n"),
    )
    article.parse()

    text: str = article.text
    title: str = article.title
    is_paywalled: int = 0

    if not skip_paywalled:
        if "Csatlakozz a Körhöz, és olvass tovább!" in article.html:
            logging.info("found paywalled 444 article")
            text = get_444(url.split("?")[0], cookies)
            is_paywalled = 1
        elif "hvg.hu/360/" in url:
            logging.info("found paywalled hvg360 article")
            try:
                text += "\n" + get_hvg(url.split("/360/")[1].split("?")[0])
            except Exception as e:
                logging.error("Error fetching HVG360 article: " + str(e))
            is_paywalled = 1

    try:
        custom_text: Optional[str] = get_custom_text(url, article.html)
        if custom_text:
            text = custom_text
    except Exception as e:
        logging.error(e)

    try:
        custom_title = get_custom_title(url, article.html)
        if custom_title:
            title = custom_title
    except Exception as e:
        logging.error(e)

    title = trim_title(title)
    title = do_replacements(title, replacements).strip()
    text = do_replacements(text, replacements).strip()

    authors: str = ",".join([a for a in article.authors if " " in a])

    description: str = article.meta_description
    for common_description in common_descriptions:
        description = description.replace(common_description.strip(), "")

    try:
        custom_description: Optional[str] = get_custom_description(url, article.html)
        if custom_description:
            description = custom_description
    except Exception as e:
        logging.error(e)

    if len(description) < 1 and text.count("\n") > 1:
        article_lines: str = text.splitlines()[0]
        description = article_lines[: article_lines[:400].rfind(".") + 1]
        if "." not in article_lines[:400]:
            description = article_lines[:400]

    date: Optional[datetime] = None
    if article.publish_date:
        date = article.publish_date.astimezone(timezone.utc)

    same_news_id: Optional[int] = same_news(title, description, text)

    if not title:
        logging.warning("Title is empty")
        raise Exception("Title is empty")

    paywall_texts = [
        "Csatlakozz a Körhöz, és olvass tovább!",
        "A teljes cikket előfizetőink olvashatják el.",
        "A keresett cikk a portfolio.hu hírarchívumához tartozik, melynek olvasása előfizetéses regisztrációhoz kötött.",
        "Ez a cikk folytatódik, de csak Portfolio Signature előfizetéssel olvasható tovább.",
        "Ez egy remek cikk a nyomtatott Magyar Narancsból, amely online is elérhető.",
        "A cikk innentől csak a Qubit+ előfizetőinek elérhető. Csatlakozz, és olvass tovább!",
    ]

    if "hvg.hu/360/" in url or any([text in article.html for text in paywall_texts]):
        is_paywalled = 1

    return ArticleDownload(
        text, title, description, authors, date, is_paywalled, same_news_id
    )


def save_article(
    article_download: ArticleDownload,
    newspaper_id: int,
    source: int,
    news_id: int,
):
    str_date: Optional[str] = None
    if article_download.date is not None and source == 1:
        str_date = article_download.date.strftime("%Y-%m-%d %H:%M:%S")
    if (
        article_download.same_news_id
        and article_download.same_news_id != newspaper_id
        and source != 1
    ):
        with db.connection_pool.get_connection() as connection:
            db.skip_same_news(
                connection,
                news_id,
                article_download.text,
                article_download.title,
                article_download.description,
                article_download.authors,
                str_date,
                article_download.is_paywalled,
            )
    else:
        with db.connection_pool.get_connection() as connection:
            db.save_download_step(
                connection,
                news_id,
                article_download.text,
                article_download.title,
                article_download.description,
                article_download.authors,
                str_date,
                article_download.is_paywalled,
            )


def login_24(username: str, password: str) -> dict[str, str]:
    username = username.strip('"')
    password = password.strip('"')
    logging.warning("Logging in to 24.hu with username: " + username)
    with sync_playwright() as p:
        browser: Browser = p.firefox.launch(proxy=playwright_proxy)
        context: BrowserContext = browser.new_context()
        page: Page = context.new_page()

        page.goto("https://24.hu/")

        page.wait_for_timeout(1000)
        try:
            page.locator(".css-1tfx6ee").press("Escape")
            logging.info("Closed cookie")
        except Exception:
            pass

        page.wait_for_timeout(1000)
        try:
            page.locator("a.html-overlay-rectangle-preview-close").click()
            logging.info("Closed banner")
        except Exception:
            pass

        page.wait_for_timeout(1000)

        try:
            page.locator("button#onesignal-slidedown-cancel-button").click()
            logging.info("Closed notification")
        except Exception:
            pass

        page.screenshot(path="data/screenshot_login_btn_24.png")

        page.locator("a.m-login__iconBtn").first.click()

        page.wait_for_timeout(1000)

        page.locator("#landing-email").fill(username)

        page.wait_for_timeout(1000)

        page.screenshot(path="data/screenshot_login_24.png")

        page.locator("#btn-next").click()

        page.wait_for_timeout(1000)

        page.locator("#password").fill(password)

        page.wait_for_timeout(1000)

        page.locator("#kc-login").click()
        page.wait_for_timeout(1000)
        page.screenshot(path="data/screenshot_login_end_24.png")

        cookies: List[Cookie] = context.cookies()
        cookies_24: dict[str, str] = {
            cookie["name"]: cookie["value"] for cookie in cookies
        }

        browser.close()
        logging.info("successfully logged in to 24.hu")

    logging.info(cookies_24)
    return cookies_24


def login_magyarnarancs(username: str, password: str):
    username = username.strip('"')
    password = password.strip('"')
    response = scraper.post(
        "https://magyarnarancs.hu/?block=User_Login&ajax=1",
        data={
            "login_email": username,
            "login_pwd": password,
            "login_sbmt": "1",
            "stayLogin": "1",
        },
    )
    if response.json()["success"]:
        logging.info("successfully logged in to magyarnarancs.hu")

    return response.cookies.get_dict()


def login_portfolio(username: str, password: str):
    username = username.strip('"')
    password = password.strip('"')
    response = scraper.post(
        "https://profil.portfolio.hu/belepes",
        data={
            "username": username,
            "password": password,
        },
    )
    if response.status_code < 400:
        logging.info("successfully logged in to protfolio.hu")

    return response.cookies.get_dict()


def login_jelen(username: str, password: str):
    username = username.strip('"')
    password = password.strip('"')
    response = scraper.post(
        "https://elofizetes.jelen.media/bejelentkezes",
        data={
            "LoginForm[username]": username,
            "LoginForm[password]": password,
        },
    )
    if response.status_code < 400:
        logging.info("successfully logged in to jelen.media")

    return response.cookies.get_dict()


def login_hang(username: str, password: str):
    username = username.strip('"')
    password = password.strip('"')
    response = scraper.post(
        "https://hang.hu/?block=User_Login&ajax=1",
        data={
            "login_email": username,
            "login_pwd": password,
            "login_sbmt": "1",
            "stayLogin": "1",
        },
    )
    if response.status_code < 400:
        logging.info("successfully logged in to hang.hu")

    return response.cookies.get_dict()


def login_444(username: str, password: str) -> dict[str, str]:
    username = username.strip('"')
    password = password.strip('"')
    with sync_playwright() as p:
        browser: Browser = p.firefox.launch(proxy=playwright_proxy)
        context: BrowserContext = browser.new_context()
        page: Page = context.new_page()
        page.goto("http://444.hu")

        page.wait_for_timeout(1000)

        def handler() -> None:
            page.get_by_role("button", name="ELFOGADOM", exact=True).click()

        page.add_locator_handler(
            page.get_by_role("button", name="ELFOGADOM", exact=True), handler
        )

        page.wait_for_timeout(1000)
        try:
            page.get_by_role("button", name="ELFOGADOM", exact=True).click()
        except Exception:
            logging.info("No cookie consent button found or already clicked.")

        page.get_by_title("Felhasználói fiók").click()
        page.screenshot(path="data/screenshot.png")

        page.get_by_role("button", name="Bejelentkezés", exact=False).click()
        page.wait_for_timeout(1000)

        page.add_locator_handler(
            page.get_by_role("button", name="ELFOGADOM", exact=True), handler
        )

        try:
            page.get_by_role("button", name="ELFOGADOM", exact=True).click()
        except Exception:
            pass

        page.locator("#frm-signInForm-username").fill(username)
        page.locator("#frm-signInForm-password").fill(password)
        page.wait_for_timeout(1000)
        page.screenshot(path="data/screenshot_login_filled_444.png")

        page.locator(".md-filled-button-profile").click()
        page.wait_for_timeout(1000)
        page.screenshot(path="data/screenshot_login_end_444.png")

        cookies: List[Cookie] = context.cookies()
        cookies_dict: dict[str, str] = {
            cookie["name"]: cookie["value"] for cookie in cookies
        }

        browser.close()

        logging.info("successfully logged in to 444.hu")

        cookies_444: dict[str, str] = cookies_dict

        return cookies_444


def get_444(url: str, cookies: dict[str, str]) -> str:
    article_name: str = url.split("/")[-1]
    date: str = "-".join(url.split("/")[-4:-1])
    bucket = "444"
    if url.count("/") == 7:
        bucket: str = url.split("/")[3]

    response: requests.Response = scraper.get(
        f"https://gateway.ipa.444.hu/api/graphql?crunch=2&operationName=fetchContent&variables=%7B%22onlyReports%22%3Afalse%2C%22order%22%3A%22DESC%22%2C%22slug%22%3A%22{article_name}%22%2C%22date%22%3A%22{date}%22%2C%22buckets%22%3A%5B%22{bucket}%22%5D%2C%22cursorInclusive%22%3Afalse%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22376c5324c94249caa29a66aeb02f8ed7c593ce2d9036098f1ba63a545405c96a%22%7D%7D",
        cookies=cookies,
    )
    text: str = "\n".join(
        [
            BeautifulSoup(f["content"], features="lxml").text
            for f in response.json()["data"]["crunched"][-1]["content"]["body"][0]
            if isinstance(f, dict) and "content" in f
        ]
    )

    return text


def get_hvg(webid: str) -> str:
    token: str = os.environ["TOKEN_HVG"]
    response: requests.Response = scraper.get(
        f"https://api.hvg.hu/web//articles/premiumcontent/?webid={webid}&apiKey=4f67ed9596ac4b11a4b2ac413e7511af",
        headers={"Authorization": "Bearer " + token},
    )
    soup = BeautifulSoup(response.json(), features="lxml")
    premium_text: str = "\n".join([t.text for t in soup.find_all("p")])
    premium_text: str = premium_text.replace(
        "A hvg360 tartalma, így a fenti cikk is, olyan érték, ami nem jöhetett volna létre a te előfizetésed nélkül. Ha tetszett az írásunk, akkor oszd meg a minőségi újságírás élményét szeretteiddel is, és ajándékozz hvg360-előfizetést!",
        "",
    )

    return premium_text


def do_retries(app_context: AppContext, cookies: dict[str, str] = {}) -> None:
    app_context.push()

    current_date: datetime = datetime.now()
    new_date: datetime = current_date - timedelta(days=7)
    formatted_date: str = new_date.strftime("%Y-%m-%d")

    with db.connection_pool.get_connection() as connection:
        rows = db.get_retries_from(connection, formatted_date)
    for row in rows:
        logging.info("retrying: " + row["url"])
        try:
            html: str = get_html(row["url"], cookies)
            article_download: ArticleDownload = process_article(
                row["url"], html, cookies
            )
            save_article(
                article_download,
                row["newspaper_id"],
                row["source"],
                row["id"],
            )
        except Exception as e:
            logging.error(e)
        sleep(3)


class DownloadProcessor(Processor):
    def __init__(self) -> None:
        self.cookies: dict[str, dict[str, str]] = {}

    def load_model(self):
        cookies_24: dict[str, str] = {}
        cookies_444: dict[str, str] = {}
        cookies_magyarnarancs: dict[str, str] = {}
        cookies_portfolio: dict[str, str] = {}
        cookies_jelen: dict[str, str] = {}
        cookies_hang: dict[str, str] = {}

        try:
            cookies_24 = login_24(os.environ["USER_24"], os.environ["PASS_24"])
        except Exception:
            logging.warning(traceback.format_exc())
            logging.warning("Failed to login to 24.hu")

        try:
            cookies_444 = login_444(os.environ["USER_444"], os.environ["PASS_444"])
        except Exception:
            logging.warning(traceback.format_exc())
            logging.warning("Failed to login to 444.hu")

        try:
            cookies_magyarnarancs = login_magyarnarancs(
                os.environ["USER_MN"], os.environ["PASS_MN"]
            )
        except Exception:
            logging.warning(traceback.format_exc())
            logging.warning("Failed to login to magyarnarancs.hu")

        try:
            cookies_portfolio = login_portfolio(
                os.environ["USER_PORTFOLIO"], os.environ["PASS_PORTFOLIO"]
            )
        except Exception:
            logging.warning(traceback.format_exc())
            logging.warning("Failed to login to portfolio.hu")

        try:
            cookies_jelen = login_jelen(
                os.environ["USER_JELEN"], os.environ["PASS_JELEN"]
            )
        except Exception:
            logging.warning(traceback.format_exc())
            logging.warning("Failed to login to jelen.media")

        try:
            cookies_hang = login_hang(os.environ["USER_HANG"], os.environ["PASS_HANG"])
        except Exception:
            logging.warning(traceback.format_exc())
            logging.warning("Failed to login to hang.hu")

        self.cookies: dict[str, dict[str, str]] = {
            "24.hu": cookies_24,
            "444.hu": cookies_444,
            "qubit.hu": cookies_444,
            "magyarnarancs.hu": cookies_magyarnarancs,
            "portfolio.hu": cookies_portfolio,
            "jelen.media": cookies_jelen,
            "hang.hu": cookies_hang,
        }
        self.done = True
        logging.info("initialized download processor")

    def process_next(self) -> None:
        with db.connection_pool.get_connection() as connection:
            next_rows: list = db.get_download_queue(connection)
        if type(next_rows) is not list:
            next_rows = [next_rows]
        for next_row in next_rows:
            self.process_row(next_row)

    def check_short(self, article: ArticleDownload) -> bool:
        return (
            not (article.title or article.text or article.description)
            or len(article.title + article.text + article.description) < 100
        )

    def process_row(self, next_row):
        if next_row is None:
            sleep(30)
            return
        logging.info("download processor is processing: " + next_row["url"])
        try:
            domain: str = next_row["url"].split("/")[2]
            cookies = self.cookies.get(domain, {})
            html: str = get_html(
                next_row["url"], cookies if domain not in ["444.hu", "qubit.hu"] else {}
            )
            if cookies:
                logging.info("using cookies for domain: " + domain)
            article_download: ArticleDownload = process_article(
                next_row["url"], html, cookies
            )

            if self.check_short(article_download):
                logging.warning("Article downloaded is too short: " + next_row["url"])

            save_article(
                article_download,
                next_row["newspaper_id"],
                next_row["source"],
                next_row["id"],
            )
        except Exception as e:
            logging.error(e)
            with db.connection_pool.get_connection() as connection:
                db.skip_download_error(connection, next_row["id"])
            sleep(2)
