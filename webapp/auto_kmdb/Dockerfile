FROM python:3.12-slim

WORKDIR /usr/src/app

COPY . auto_kmdb

RUN apt update
RUN apt install -y wget git gcc g++

RUN pip install pip==23.3.2
RUN pip install -r auto_kmdb/requirements.txt
RUN python auto_kmdb/init_container.py

RUN playwright install-deps
RUN playwright install firefox

RUN wget 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTJLsof1CkRQ4hkw_bPSxtbpk5mo1ucUN0iUvZHHEd2SySJLrGOEsGPSbdsQ1JPJOy2ksgvJVPVxuTw/pub?gid=1567624346&single=true&output=csv' -O auto_kmdb/places_synonym.csv
RUN wget 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTJLsof1CkRQ4hkw_bPSxtbpk5mo1ucUN0iUvZHHEd2SySJLrGOEsGPSbdsQ1JPJOy2ksgvJVPVxuTw/pub?gid=1205893612&single=true&output=csv' -O auto_kmdb/institutions_synonym.csv

EXPOSE 8000

CMD ["flask", "--app", "auto_kmdb", "run", "-h", "0.0.0.0", "-p", "8000"]