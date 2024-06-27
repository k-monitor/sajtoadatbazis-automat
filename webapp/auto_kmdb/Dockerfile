FROM python:3.9-slim

WORKDIR /usr/src/app

COPY . auto_kmdb

RUN apt update
RUN apt install -y wget git tar

RUN pip install -r auto_kmdb/requirements.txt
RUN python auto_kmdb/init_container.py
RUN mkdir /data
RUN mkdir /models
RUN wget 'https://huggingface.co/boapps/kmdb-category-classifier/resolve/main/svm_classifier_category.joblib?download=true' -O /models/svm_classifier_category.joblib
RUN wget 'https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux-aarch64.tar.gz' -O /geckodriver.tar.gz
RUN tar xvfz /geckodriver.tar.gz -C /data

ENV DATA_PATH="/data"

EXPOSE 8000

CMD ["gunicorn", "auto_kmdb:app", "--bind", "0.0.0.0:8000"]