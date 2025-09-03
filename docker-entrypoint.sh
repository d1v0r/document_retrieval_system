#!/bin/sh
set -e

# Prevent any package upgrades
pip freeze > /tmp/requirements.txt
pip install --no-cache-dir -r /tmp/requirements.txt
rm /tmp/requirements.txt

# Run the command
exec "$@"