#!/bin/bash

check_for_errors() {
    result=$(podman-compose logs 2>&1)
    if [[ "${result}" == *"ERROR"* ]] || [[ "${result}" == *"CRITICAL"* ]] || [[ "${result}" == *"mysql.connector.errors.OperationalError"* ]]; then
        # Get the current date and time in the desired format
        current_time=$(date +"%Y-%m-%d_%H-%M-%S")

        # Define the output file name
        output_file="podman_logs_$current_time.txt"

        # Execute podman-compose logs and redirect the output to the file
        echo result > "$output_file"

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
