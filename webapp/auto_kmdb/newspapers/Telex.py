from typing import LiteralString
from bs4.element import Tag
from auto_kmdb.newspapers.Newspaper import Newspaper
from bs4 import BeautifulSoup, ResultSet
from urllib.parse import urlparse


class Telex(Newspaper):
    ignored_tags = ["<strong>", "</strong>"]

    def is_url_this(self, url: str, html: str) -> bool:
        return urlparse(url).netloc == "telex.hu"

    def get_text(self, url: str, html: str) -> str:
        for tag in self.ignored_tags:
            html = html.replace(tag, " ").replace("  ", " ")
        soup = BeautifulSoup(html, "html.parser")
        paragraphs: ResultSet[Tag] = soup.select(
            "div.article-html-content p, div.article-html-content li"
        )

        parsed_text: list[str] = []
        for p in paragraphs:
            text: str = p.get_text().strip()
            if text:
                parsed_text.append(text)

        return "\n".join(parsed_text)
