from datasets import load_dataset
import os
import gzip
import json
import requests
from tqdm import tqdm

def download_htmls():
    ds = load_dataset("K-Monitor/kmdb_classification").shuffle(seed=42)

    urls = ds["train"]["url"]

    output_file = "data/data.jsonl.gz"
    downloaded_urls = set()

    # Load already downloaded URLs if the file exists
    if os.path.exists(output_file):
        with gzip.open(output_file, 'rt', encoding='utf-8') as f:
            for line in f:
                downloaded_urls.add(json.loads(line)["url"])

    with gzip.open(output_file, 'at', encoding='utf-8') as f:
        for url in tqdm(urls):
            if url in downloaded_urls:
                continue
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                html_content = response.text
                json_record = json.dumps({"url": url, "html": html_content})
                f.write(json_record + "\n")
            except Exception:
                continue
