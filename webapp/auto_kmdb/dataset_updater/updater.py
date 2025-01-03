from datasets import load_dataset, Dataset
import os
import gzip
import json
import requests
from tqdm import tqdm
from auto_kmdb.processors.DownloadProcessor import process_article
import jsonlines
import traceback


def update_dataset():
    # download_html()
    update_classification()


def download_html():
    ds = load_dataset("K-Monitor/kmdb_classification").shuffle(seed=42)

    urls = ds["train"]["url"]

    output_file = "data/data.jsonl.gz"
    downloaded_urls = set()

    # Load already downloaded URLs if the file exists
    if os.path.exists(output_file):
        with gzip.open(output_file, "rt", encoding="utf-8") as f:
            for line in f:
                downloaded_urls.add(json.loads(line)["url"])

    with gzip.open(output_file, "at", encoding="utf-8") as f:
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
                html_content = None
                json_record = json.dumps({"url": url, "html": html_content})
                f.write(json_record + "\n")
                continue


def update_classification():
    ds = load_dataset("K-Monitor/kmdb_classification")
    print(ds)

    ds_dict = {}
    for d in ds["train"]:
        ds_dict[d["url"]] = d

    urls = ds["train"]["url"]

    input_file = "data/data.jsonl.gz"
    downloaded_urls = set()

    # Load already downloaded URLs if the file exists
    if os.path.exists(input_file):
        with gzip.open(input_file, "rt", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data["html"]:
                    downloaded_urls.add(data["url"])

    ds = ds.filter(lambda row: row["url"] in downloaded_urls)

    print(ds)

    new_list = []
    with gzip.open(input_file, "rt", encoding="utf-8") as f:
        for line in tqdm(f):
            try:
                data = json.loads(line)
                if not data["html"] or data["url"] not in ds_dict:
                    continue
                article = process_article(
                    data["url"], data["html"], {}, skip_paywalled=True
                )
                original_data = ds_dict[data["url"]]
                original_data["title"] = article.title
                original_data["description"] = article.description
                new_list.append(original_data)
            except Exception as e:
                print(e)
                # traceback.print_exc()

    new_dataset = Dataset.from_list(new_list)
    print(new_dataset)
    new_dataset.to_json("data/kmdb_classification_v2.jsonl")
    new_dataset.push_to_hub("K-Monitor/kmdb_classification_v2")
