#!/bin/sh

# Start the SSH tunnel
ssh -N -L 9999:127.0.0.1:3306 -p 2267 -i /secrets/autokmdb_key -o PubkeyAcceptedKeyTypes=ssh-rsa -o StrictHostKeyChecking=no -o GatewayPorts=true autokmdb@ahalo.hu &

# Start the SOCKS5 proxy
ssh -D 1080 -f -C -N -p 2267 -i /secrets/autokmdb_key -o PubkeyAcceptedKeyTypes=ssh-rsa -o StrictHostKeyChecking=no -o GatewayPorts=true autokmdb@ahalo.hu

# Keep the container running
tail -f /dev/null
