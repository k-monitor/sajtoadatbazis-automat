FROM python:3.12

WORKDIR /usr/src/app

COPY auto_kmdb auto_kmdb

RUN apt update
RUN apt install -y wget git gcc g++

RUN --mount=type=bind,rw,source=data,target=/usr/src/app/data wget 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTJLsof1CkRQ4hkw_bPSxtbpk5mo1ucUN0iUvZHHEd2SySJLrGOEsGPSbdsQ1JPJOy2ksgvJVPVxuTw/pub?gid=1567624346&single=true&output=csv' -O data/places_synonym.csv
RUN --mount=type=bind,rw,source=data,target=/usr/src/app/data wget 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTJLsof1CkRQ4hkw_bPSxtbpk5mo1ucUN0iUvZHHEd2SySJLrGOEsGPSbdsQ1JPJOy2ksgvJVPVxuTw/pub?gid=1205893612&single=true&output=csv' -O data/institutions_synonym.csv

RUN pip install pip==23.3.2
RUN pip install -r auto_kmdb/requirements.txt
RUN python auto_kmdb/init_container.py

RUN playwright install-deps
RUN playwright install firefox

EXPOSE 8000

CMD ["python", "-m", "auto_kmdb"]
