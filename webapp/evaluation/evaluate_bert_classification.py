from datasets import load_dataset
import requests

LLM_SERVER = 'http://127.0.0.1:8085'
article_classification_prompt = '''{title}
{description}'''

dataset = load_dataset('boapps/kmdb_classification')

for article in dataset['train']:
    text = article_classification_prompt.format(
        title=article.title, description=article["description"], text=article["text"], keywords=', '.join(article["keywords"]))
    resp = requests.post(LLM_SERVER+'/classify',
                         json={"text": text}, timeout=1800)
    respText = resp.json()['class']
    print(respText)
