from typing import Optional


class Newspaper:
    def __init__(self) -> None:
        pass

    def is_url_this(self, url: str, html: str) -> Optional[bool]:
        pass

    def get_text(self, url: str, html: str) -> Optional[str]:
        pass

    def get_description(self, url: str, html: str) -> Optional[str]:
        pass

    def get_feed(self):
        pass
