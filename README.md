# Sajtóadatbázis automatizáló projekt

A [k-monitor sajtóadatbázisának](https://adatbazis.k-monitor.hu/) bővítését automatizáló rendszer.

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

További info: [wiki](https://github.com/k-monitor/sajtoadatbazis-automat/wiki)

### Backend

A backend egy flask applikáció.

### Frontend

A frontend egy Single Page App, ami Nuxt-ban készült. Egy REST API-n keresztül kommunikál a backend-el.

### GitHub Actions

~~Egy GitHub Action lefut minden push/merge esetén, ami a main branchet érinti.~~
~~Ez fel ssh-zik a szerverre, leállítja az ott futó backendet, frissíti a repo-t, majd újra build-eli a konténereket és elindítja a webapp-ot.~~

Jelenleg ki van kapcsolva
