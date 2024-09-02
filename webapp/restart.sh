#!/bin/bash

cd /home/autokmdb/sajtoadatbazis-automat/webapp
/usr/bin/podman-compose down
/usr/bin/podman-compose up -d
