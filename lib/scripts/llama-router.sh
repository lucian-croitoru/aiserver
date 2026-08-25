#!/bin/bash

# Place this file in /usr/local/bin
# Run `chmod + x llama-router.sh` after placing the file
# Starts router.py


# Build command string
PYTHON_BINARY="/home/lucian/aiserver/.venv/bin/python3"
SERVER_FILE="/home/lucian/aiserver/router/router.py"
COMMAND="$PYTHON_BINARY $SERVER_FILE"

# Start server
echo "Running: $COMMAND"
$COMMAND
