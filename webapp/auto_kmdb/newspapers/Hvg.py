from typing import Optional
from auto_kmdb.newspapers.Newspaper import Newspaper
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class Hvg(Newspaper):
    def is_url_this(self, url: str, html: str) -> bool:
        return urlparse(url).netloc.endswith("hvg.hu")

    def get_title(self, url: str, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, 'html.parser')

        title_tag = soup.title

        if title_tag and title_tag.string:
            title_text = title_tag.string.strip()

            if '|' in title_text:
                title_text = '|'.join(title_text.split('|')[:-1]).strip()

            if ':' in title_text:
                title_text = ':'.join(title_text.split(':')[1:]).strip()
            return title_text
        else:
            return None
