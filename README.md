# Sajtóadatbázis automatizáló projekt

adathalmaz (kb. 47 000 db cikk): [kmdb_base](https://huggingface.co/datasets/boapps/kmdb_base)

## Futtatás

```bash
git clone https://github.com/k-monitor/sajtoadatbazis-automat
cd sajtoadatbazis-automat/webapp
docker-compose up
```

```bash
cd webapp
wget 'https://huggingface.co/K-Monitor/kmdb_classification_category_v2/resolve/main/svm_classifier_category.joblib?download=true' -O data/svm_classifier_category.joblib
```

## Fejlesztés

### Backend

A backend egy flask applikáció, amit gunicorn futtat.

### Frontend

A frontend egy Single Page App, ami Nuxt-ban készült. Egy REST API-n keresztül kommunikál a backend-el.

### Adatbázis

A rendszer számára létrehozott adatbázistáblák: [create_tables.sql](https://github.com/k-monitor/sajtoadatbazis-automat/blob/main/webapp/auto_kmdb/scripts/create_tables.sql)

### GitHub Actions

Egy GitHub Action lefut minden push/merge esetén, ami a main branchet érinti.
Ez fel ssh-zik a szerverre, leállítja az ott futó backendet, frissíti a repo-t, majd újra build-eli a konténereket és elindítja a webapp-ot.

