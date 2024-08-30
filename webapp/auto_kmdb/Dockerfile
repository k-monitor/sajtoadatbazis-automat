FROM python:3.9-slim

WORKDIR /usr/src/app

COPY . auto_kmdb

RUN apt update
RUN apt install -y wget git gcc

RUN pip install -r auto_kmdb/requirements.txt
RUN python auto_kmdb/init_container.py
RUN mkdir /data
RUN mkdir /data/models
RUN wget 'https://huggingface.co/K-Monitor/kmdb_classification_category/resolve/main/svm_classifier_category.joblib?download=true' -O /data/models/svm_classifier_category.joblib

RUN playwright install firefox
RUN playwright install-deps

RUN wget 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTJLsof1CkRQ4hkw_bPSxtbpk5mo1ucUN0iUvZHHEd2SySJLrGOEsGPSbdsQ1JPJOy2ksgvJVPVxuTw/pub?gid=1567624346&single=true&output=csv' -O auto_kmdb/places_synonym.csv
RUN wget 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTJLsof1CkRQ4hkw_bPSxtbpk5mo1ucUN0iUvZHHEd2SySJLrGOEsGPSbdsQ1JPJOy2ksgvJVPVxuTw/pub?gid=1205893612&single=true&output=csv' -O auto_kmdb/institutions_synonym.csv

ENV DATA_PATH="/data"

EXPOSE 8000

CMD ["gunicorn", "auto_kmdb:app", "--bind", "0.0.0.0:8000"]