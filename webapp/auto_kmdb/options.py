import json


def load_json_from_file(filename: str) -> dict:
    with open(filename) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


feed_urls = load_json_from_file('auto_kmdb/data/feed_urls.json')
skip_url_patterns = load_json_from_file('auto_kmdb/data/skip_url_patterns.json')
