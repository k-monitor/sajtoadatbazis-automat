from typing import Optional
from auto_kmdb.newspapers.Newspaper import Newspaper
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class Atv(Newspaper):
    def is_url_this(self, url: str, html: str) -> bool:
        return urlparse(url).netloc in ["atv.hu", "www.atv.hu"]

    def get_description(self, url: str, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        meta_tag = soup.find("meta", attrs={"name": "twitter:description"})
        if meta_tag:
            return meta_tag.get("content")
        return None
