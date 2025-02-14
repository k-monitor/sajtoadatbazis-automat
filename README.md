# Sajtóadatbázis automatizáló projekt

A [k-monitor sajtóadatbázisának](https://adatbazis.k-monitor.hu/) bővítését automatizáló rendszer.

## Futtatás

### Élesben

```bash
git clone https://github.com/k-monitor/sajtoadatbazis-automat
cd sajtoadatbazis-automat/webapp
cp data/.env.example data/.env
podman-compose up
```

### Fejlesztéshez

SSH tunnelek (db és proxy miatt):

```bash
ssh -N -L 9999:127.0.0.1:3306 -p 2267 kmdb
ssh -D 1080 -C -N -p 2267 -o PubkeyAcceptedKeyTypes=ssh-rsa -o StrictHostKeyChecking=no -o GatewayPorts=true kmdb
```

Backend elindítása fejlesztéshez:

```bash
apt install wget git gcc g++

cd webapp

wget 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTJLsof1CkRQ4hkw_bPSxtbpk5mo1ucUN0iUvZHHEd2SySJLrGOEsGPSbdsQ1JPJOy2ksgvJVPVxuTw/pub?gid=1567624346&single=true&output=csv' -O data/places_synonym.csv
wget 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTJLsof1CkRQ4hkw_bPSxtbpk5mo1ucUN0iUvZHHEd2SySJLrGOEsGPSbdsQ1JPJOy2ksgvJVPVxuTw/pub?gid=1205893612&single=true&output=csv' -O data/institutions_synonym.csv

pip install pip==23.3.2
pip install -r requirements.txt

playwright install-deps
playwright install firefox

python -m auto_kmdb
```

Frontend elindítása fejlesztéshez:

```bash
cd webapp/frontend
npm install
npm run dev
```

További info: [wiki](https://github.com/k-monitor/sajtoadatbazis-automat/wiki)

### Backend

A backend egy flask applikáció.

### Frontend

A frontend egy Single Page App, ami Nuxt-ban készült. Egy REST API-n keresztül kommunikál a backend-el.

### GitHub Actions

~~Egy GitHub Action lefut minden push/merge esetén, ami a main branchet érinti.~~
~~Ez fel ssh-zik a szerverre, leállítja az ott futó backendet, frissíti a repo-t, majd újra build-eli a konténereket és elindítja a webapp-ot.~~

Jelenleg ki van kapcsolva
