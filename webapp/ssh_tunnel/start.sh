#!/bin/sh

# Host keys are pinned in /etc/ssh/ssh_known_hosts (see Dockerfile).
# GatewayPorts=yes is required so the forwards listen on all interfaces of the
# container, otherwise Docker port publishing / other containers can't reach them.
SSH_OPTS="-p 22 -i /secrets/autokmdb_key \
    -o BatchMode=yes \
    -o StrictHostKeyChecking=yes \
    -o GatewayPorts=yes \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3"
SSH_TARGET="autokmdb@62.83.75.97"

# Start the SSH tunnel with auto-restart
while true; do
    echo "Starting SSH tunnel..."
    ssh -N -L 9999:127.0.0.1:3307 $SSH_OPTS $SSH_TARGET
    echo "SSH tunnel disconnected, restarting in 5 seconds..."
    sleep 5
done &

# Start the SOCKS5 proxy with auto-restart
while true; do
    echo "Starting SOCKS5 proxy..."
    ssh -D 1080 -C -N $SSH_OPTS $SSH_TARGET
    echo "SOCKS5 proxy disconnected, restarting in 5 seconds..."
    sleep 5
done &

# Keep the container running
tail -f /dev/null
