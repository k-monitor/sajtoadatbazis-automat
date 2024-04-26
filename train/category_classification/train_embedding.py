import jsonlines
from tqdm import tqdm
from joblib import dump
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from transformers import BertForSequenceClassification, BertTokenizer
import torch

model = BertForSequenceClassification.from_pretrained('boapps/kmdb_classification_model').to('cuda')
tokenizer = BertTokenizer.from_pretrained('SZTAKI-HLT/hubert-base-cc')


labels = []
texts = []

def get_bert_embeddings(texts):
    model.eval()
    with torch.no_grad():
        embeddings = []
        for text in tqdm(texts):
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512).to('cuda')
            output = model(**inputs, output_hidden_states=True)
            cls_embedding = output.hidden_states[-1][:, 0, :]
            embeddings.append(cls_embedding.squeeze().to('cpu').numpy())
    return embeddings


with jsonlines.open('catds.jsonl') as reader:
    for n in reader:
        labels.append(n['category'])
        texts.append(n['text'])
embeddings = get_bert_embeddings(texts)

# Prepare train and test sets
X_train, X_test, y_train, y_test = train_test_split(embeddings, labels, test_size=0.25, random_state=42)

# Initialize and train the SVM
svm_classifier = SVC(kernel='linear')
svm_classifier.fit(X_train, y_train)

# Evaluate the classifier
predictions = svm_classifier.predict(X_test)
accuracy = accuracy_score(y_test, predictions)
print("Accuracy:", accuracy)

dump(svm_classifier, 'svm_classifier_category.joblib')
