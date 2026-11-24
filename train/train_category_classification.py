from tqdm import tqdm
from joblib import dump
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from transformers import BertForSequenceClassification, BertTokenizer
from datasets import load_dataset
import torch
from huggingface_hub import HfApi

labels = []
texts = []

base = load_dataset("K-Monitor/kmdb_base")
cat_by_url = {}
for n in base['train']:
    cat_by_url[n['source_url']] = n['category']

ds = load_dataset("K-Monitor/kmdb_classification_v2").filter(lambda row: row['label'] == 1)
print(len(ds['train']))
ds = ds.filter(lambda row: row['url'] in cat_by_url)
print(len(ds['train']))
ds = ds.map(lambda row: {'category': cat_by_url[row['url']]})
ds = ds.filter(lambda row: row['category'] and row['text'])
for n in ds['train']:
    labels.append(n['category'])
    texts.append(n['title'] +'\n'+ n['description'])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = BertForSequenceClassification.from_pretrained('K-Monitor/kmdb_classification_hubert_v2').to(device)
tokenizer = BertTokenizer.from_pretrained('SZTAKI-HLT/hubert-base-cc')

def get_bert_embeddings(texts):
    model.eval()
    with torch.no_grad():
        embeddings = []
        for text in tqdm(texts):
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512).to(device)
            output = model(**inputs, output_hidden_states=True)
            cls_embedding = output.hidden_states[-1][:, 0, :]
            embeddings.append(cls_embedding.squeeze().to('cpu').numpy())
    return embeddings

embeddings = get_bert_embeddings(texts)

X_train, X_test, y_train, y_test = train_test_split(embeddings, labels, test_size=0.25, random_state=42)

# Initialize and train the SVM
svm_classifier = SVC(kernel='linear')
svm_classifier.fit(X_train, y_train)

predictions = svm_classifier.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
print("Accuracy:", accuracy)

dump(svm_classifier, 'svm_classifier_category.joblib')

api = HfApi()

api.upload_file(
    path_or_fileobj="svm_classifier_category.joblib",
    path_in_repo="svm_classifier_category.joblib",
    repo_id="K-Monitor/kmdb_classification_category_v2",
    repo_type="model",
)
