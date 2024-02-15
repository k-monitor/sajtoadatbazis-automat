from flask import Flask, request, jsonify
from transformers import BertForSequenceClassification, BertTokenizer
import torch
import torch.nn.functional as F

model = BertForSequenceClassification.from_pretrained(
    'boapps/kmdb_classification_model')
tokenizer = BertTokenizer.from_pretrained('SZTAKI-HLT/hubert-base-cc')

app = Flask(__name__)


@app.route("/status", methods=["GET"])
def status():
    return jsonify("OK"), 200

@app.route("/classify", methods=["POST"])
def index():
    data = request.get_json()
    inputs = tokenizer(data['text'], return_tensors="pt")
    logits = model(**inputs).logits
    probabilities = F.softmax(logits[0], dim=-1)
    res = torch.argmax(logits, axis=1)[0]
    corruption = probabilities[0] < 0.42
    return jsonify({"class": "corruption" if corruption else "other", "prob": float(probabilities[0])}), 200
