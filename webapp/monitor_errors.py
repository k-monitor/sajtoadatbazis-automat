import time
import re
import subprocess

log_file = "data/log.txt"
error_pattern = r"ERROR:root:MySQL Connection not available."


def check_log_file():
    with open(log_file, 'r') as f:
        lines = f.readlines()[-2:]
        return any(re.search(error_pattern, line) for line in lines)


def restart_containers():
    subprocess.run(["podman-compose", "down"])
    subprocess.run(["podman-compose", "up", "-d"])


while True:
    if check_log_file():
        restart_containers()
    time.sleep(60)
