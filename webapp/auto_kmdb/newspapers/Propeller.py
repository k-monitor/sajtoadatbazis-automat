from typing import Optional
from auto_kmdb.newspapers.Newspaper import Newspaper
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class Propeller(Newspaper):
    def is_url_this(self, url: str, html: str) -> bool:
        return urlparse(url).netloc in ["propeller.hu", "www.propeller.hu"]

    def get_description(self, url: str, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        lead_p = soup.select_one("div.entry-content p")
        if lead_p:
            return lead_p.text
        return None
