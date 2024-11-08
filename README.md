# Sajtóadatbázis automatizáló projekt

A [k-monitor sajtóadatbázisának](https://adatbazis.k-monitor.hu/) bővítését automatizáló rendszer.

További info: [wiki](https://github.com/k-monitor/sajtoadatbazis-automat/wiki)

### Backend

A backend egy flask applikáció, amit gunicorn futtat.

### Frontend

A frontend egy Single Page App, ami Nuxt-ban készült. Egy REST API-n keresztül kommunikál a backend-el.

### GitHub Actions

Egy GitHub Action lefut minden push/merge esetén, ami a main branchet érinti.
Ez fel ssh-zik a szerverre, leállítja az ott futó backendet, frissíti a repo-t, majd újra build-eli a konténereket és elindítja a webapp-ot.
