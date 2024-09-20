#!/bin/bash

check_for_errors() {
    result=$(podman-compose logs 2>&1)
    if [[ "${result}" == *"ERROR"* ]] || [[ "${result}" == *"CRITICAL"* ]]; then
        return 0 # Return true
    else
        return 1 # Return false
    fi
}

restart_containers() {
    echo "restarting!"
    podman-compose down
    podman-compose up -d
}

while true; do
    if check_for_errors; then
        restart_containers
    fi
    sleep 60
done
