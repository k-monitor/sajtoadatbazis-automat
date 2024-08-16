#!/bin/bash

cd /home/opc/sajtoadatbazis-automat/webapp
/usr/bin/podman-compose down
/usr/bin/podman-compose up -d
