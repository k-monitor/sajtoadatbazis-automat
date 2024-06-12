from datasets import load_dataset
import requests
import time
import jsonlines
from tqdm import tqdm
import get_wayback_machine
import validators

dataset = load_dataset("json", data_files='urls.jsonl')['train']

dataset = dataset.filter(lambda row: row['source_url'] is not None and validators.url(row['source_url']))

shuffled_dataset = dataset.shuffle(seed=42)


def get_html(url):
    retries = 0
    while True:
        time.sleep(0.1)
        if retries > 4:
            break
        try:
            response = requests.get(url, timeout=(5, 30))
            if response.ok:
                return response.text
            else:
                break
        except requests.ConnectionError:
            retries += 1
            print('ConnectionError:', url)
        except Exception:
            break

    response = get_wayback_machine.get(url)
    if response and response.ok:
        return response.text

    return ''


with jsonlines.open('kmdb_html_new.jsonl', mode='w') as writer:
    for url in tqdm(shuffled_dataset['source_url']):
        writer.write({'url': url, 'html': get_html(url)})
