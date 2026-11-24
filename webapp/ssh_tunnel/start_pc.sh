#!/bin/sh

# Start the SSH tunnel
ssh -N -L 9999:127.0.0.1:3306 -p 2267 -o PubkeyAcceptedKeyTypes=ssh-rsa -o StrictHostKeyChecking=no -o GatewayPorts=true kmdb &

# Start the SOCKS5 proxy
ssh 1080 -f -C -N -p 2267 -o PubkeyAcceptedKeyTypes=ssh-rsa -o StrictHostKeyChecking=no -o GatewayPorts=true kmdb
