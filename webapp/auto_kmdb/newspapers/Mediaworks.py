from auto_kmdb.newspapers.Newspaper import Newspaper
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class Mediaworks(Newspaper):
    def is_url_this(self, url, html):
        return urlparse(url).netloc in [
            "www.baon.hu",
            "www.bama.hu",
            "www.beol.hu",
            "www.boon.hu",
            "www.delmagyar.hu",
            "www.duol.hu",
            "www.feol.hu",
            "www.haon.hu",
            "www.heol.hu",
            "www.szoljon.hu",
            "www.kemma.hu",
            "www.nool.hu",
            "www.sonline.hu",
            "www.szon.hu",
            "www.teol.hu",
            "www.vaol.hu",
            "www.veol.hu",
            "www.zaol.hu",
            "mandiner.hu",
            "magyarnemzet.hu",
            "szabadfold.hu",
            "www.origo.hu",
            "www.vg.hu",
            "www.borsonline.hu",
            "ripost.hu",
            "metropol.hu",
        ]

    def get_text(this, url, html):
        soup = BeautifulSoup(html, "html.parser")
        paragraphs = soup.select(
            ".block-content p, .block-content li, .article-text-formatter p, .article-text-formatter li"
        )

        parsed_text = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                parsed_text.append(text)

        return "\n".join(parsed_text)
