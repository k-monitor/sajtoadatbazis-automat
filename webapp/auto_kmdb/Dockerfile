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

RUN playwright install firefox
RUN playwright install-deps

RUN wget 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTzcHYcevHz8G1U8WIfQjDLWnBj2pdNeb4Ekd8l-y-M4ufOjW6TkHxGLsZgHkyI6KPD5D-7pdZ-L2GK/pub?gid=1636309901&single=true&output=csv' -O auto_kmdb/places_synonym.csv
RUN wget 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTzcHYcevHz8G1U8WIfQjDLWnBj2pdNeb4Ekd8l-y-M4ufOjW6TkHxGLsZgHkyI6KPD5D-7pdZ-L2GK/pub?gid=1261307072&single=true&output=csv' -O auto_kmdb/institutions_synonym.csv

ENV DATA_PATH="/data"

EXPOSE 8000

CMD ["gunicorn", "auto_kmdb:app", "--bind", "0.0.0.0:8000"]