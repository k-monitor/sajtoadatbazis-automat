from transformers import pipeline, AutoTokenizer
from transformers import BertForSequenceClassification, BertTokenizer
from dotenv import load_dotenv

load_dotenv("data/.env")

classifier = pipeline(
    "ner",
    model="boapps/kmdb_ner_model",
    aggregation_strategy="average",
    tokenizer=AutoTokenizer.from_pretrained(
        "boapps/kmdb_ner_model", model_max_length=512
    ),
)

model = BertForSequenceClassification.from_pretrained(
    "K-Monitor/kmdb_classification_hubert"
)
tokenizer = BertTokenizer.from_pretrained("SZTAKI-HLT/hubert-base-cc", max_length=512)
