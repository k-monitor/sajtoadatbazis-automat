#!/bin/sh

# Start the SSH tunnel with auto-restart
while true; do
    echo "Starting SSH tunnel..."
    ssh -N -L 9999:127.0.0.1:3306 -p 2267 -i /secrets/autokmdb_key -o PubkeyAcceptedKeyTypes=ssh-rsa -o StrictHostKeyChecking=no -o GatewayPorts=true autokmdb@ahalo.hu
    echo "SSH tunnel disconnected, restarting in 5 seconds..."
    sleep 5
done &

# Start the SOCKS5 proxy with auto-restart
while true; do
    echo "Starting SOCKS5 proxy..."
    ssh -D 1080 -C -N -p 2267 -i /secrets/autokmdb_key -o PubkeyAcceptedKeyTypes=ssh-rsa -o StrictHostKeyChecking=no -o GatewayPorts=true autokmdb@ahalo.hu
    echo "SOCKS5 proxy disconnected, restarting in 5 seconds..."
    sleep 5
done &

# Keep the container running
tail -f /dev/null
