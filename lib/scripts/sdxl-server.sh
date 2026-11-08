#!/bin/bash

# Place this file in /usr/local/bin
# Run `chmod + x sdxl-server.sh` after placing the file
# Starts sdxl_server.py


# Build command string
PYTHON_BINARY="~/aiserver/.venv/bin/python3"
SERVER_FILE="~/aiserver/sdxl/sdxl_server.py"
COMMAND="$PYTHON_BINARY $SERVER_FILE"

# Start server
echo "Running: $COMMAND"
$COMMAND
