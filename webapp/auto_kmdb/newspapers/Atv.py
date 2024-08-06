from auto_kmdb.newspapers.Newspaper import Newspaper
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class Atv(Newspaper):
    def is_url_this(self, url, html):
        return urlparse(url).netloc in ["atv.hu", "www.atv.hu"]

    def get_description(this, url, html):
        soup = BeautifulSoup(html, "html.parser")
        meta_tag = soup.find("meta", attrs={"name": "twitter:description"})
        if meta_tag:
            return meta_tag.get("content")
        return None

    def get_text(this, url, html):
        return None
