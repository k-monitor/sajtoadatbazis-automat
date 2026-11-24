from datasets import load_dataset
from transformers import BertForSequenceClassification, BertTokenizer
from transformers import Trainer, TrainingArguments, pipeline
from peft import LoraConfig, TaskType, get_peft_model
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.metrics import precision_recall_curve, auc


def tokenize_function(examples):
    return tokenizer(
        examples["td"], padding="max_length", truncation=True, max_length=512
    )


def trim_title(title):
    for name in title_papers:
        title = title.replace(name, "")
    return title


def format_article(title, description, url):
    domain = ".".join(url.split("/")[2].split(".")[-2:])
    return f"{title}\n{description}\n({domain})"


def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    precision, recall, _, _ = precision_recall_fscore_support(
        labels, preds, average="binary"
    )
    acc = accuracy_score(labels, preds)
    return {"accuracy": acc, "precision": precision, "recall": recall}


dataset = load_dataset("K-Monitor/kmdb_classification_v2")

dataset = dataset.filter(lambda row: row["title"] and row["description"])

title_papers = [
    " | atlatszo.hu",
    " | G7 - Gazdasági sztorik érthetően",
    " - ORIGO",
    " | 24.hu",
    "FEOL - ",
    " - PestiSrácok",
    " | BorsOnline",
    " - Blikk",
    "BEOL - ",
    "VAOL - ",
    "KEMMA - ",
    "HírExtra - ",
    "DUOL - ",
    "SZOLJON - ",
    "HEOL - ",
    " - Mandiner",
    " - Greenfo",
    "BAMA - ",
    "BOON - ",
    " - pecsma.hu",
    " - Direkt36",
    " | hvg.hu",
]

dataset = dataset.map(
    lambda row: {"td": format_article(row["title"], row["description"], row["url"])}
)

print(dataset["train"]["td"][:100])

print(dataset.filter(lambda row: row["label"] == 0))
print(dataset.filter(lambda row: row["label"] == 1))

dataset = dataset.shuffle(seed=42)
split = dataset["train"].train_test_split(
    test_size=0.2,
    seed=42,
)
dataset = split["test"].train_test_split(
    test_size=0.5,
    seed=42,
)
dataset["validation"] = dataset["train"]
dataset["train"] = split["train"]


tokenizer = BertTokenizer.from_pretrained("SZTAKI-HLT/hubert-base-cc")
tokenized_datasets = dataset.map(tokenize_function, batched=True)

model = BertForSequenceClassification.from_pretrained(
    "SZTAKI-HLT/hubert-base-cc", num_labels=2
)

lora_config = LoraConfig(
    task_type=TaskType.SEQ_CLS,
    inference_mode=True,
    r=16,
    lora_alpha=32,
    lora_dropout=0.1,
    # use_rslora=True,
    # use_dora=True,
    bias="all",
    target_modules=[
        "query",
        "key",
        "value",
    ],
    modules_to_save=["classifier"],
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

batch_size = 48

training_args = TrainingArguments(
    output_dir="hubert-classification",
    per_device_train_batch_size=batch_size,
    per_device_eval_batch_size=batch_size,
    gradient_accumulation_steps=8,
    weight_decay=0.01,
    load_best_model_at_end=True,
    logging_steps=20,
    eval_steps=20,
    save_steps=20,
    save_total_limit=20,
    save_strategy="steps",
    evaluation_strategy="steps",
    learning_rate=0.0015,
    warmup_steps=80,
    num_train_epochs=4,
)

trainer = Trainer(
    model=model,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
    args=training_args,
    compute_metrics=compute_metrics,
)

trainer.train()

trainer.evaluate(eval_dataset=tokenized_datasets["test"])

merged = model.merge_and_unload()
merged.push_to_hub("K-Monitor/kmdb_classification_hubert_v2")

classifier = pipeline(
    "sentiment-analysis",
    model=merged,
    tokenizer=tokenizer,
    return_all_scores=True,
    max_length=512,
)
print(classifier("hello"))

dataset["test"] = dataset["test"].map(
    lambda row: {"score": classifier(row["td"])[0][1]["score"]}
)

precision, recall, thresholds = precision_recall_curve(
    dataset["test"]["label"], dataset["test"]["score"]
)

aupr = auc(recall, precision)

print(f"AUPR: {aupr}")

merged.save_pretrained("kmdb_classification_hubert-merged_model-2")
model.save_pretrained("kmdb_classification_hubert-lora-2")
