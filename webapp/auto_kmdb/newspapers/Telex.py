from auto_kmdb.newspapers.Newspaper import Newspaper
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class Telex(Newspaper):
    def is_url_this(self, url, html):
        return urlparse(url).netloc == 'telex.hu'

    def get_text(this, url, html):
        soup = BeautifulSoup(html, 'html.parser')
        paragraphs = soup.select('div.article-html-content p')

        parsed_text = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                parsed_text.append(text)

        return '\n'.join(parsed_text)
