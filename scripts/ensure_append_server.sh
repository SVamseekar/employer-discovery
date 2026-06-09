#!/bin/bash
# Start append_server.py if not already running
if ! lsof -i :9876 > /dev/null 2>&1; then
    cd /Users/souravamseekarmarti/Projects/employer-discovery
    /Users/souravamseekarmarti/Projects/employer-discovery/venv/bin/python scripts/append_server.py >> data/append_server.log 2>&1 &
fi
