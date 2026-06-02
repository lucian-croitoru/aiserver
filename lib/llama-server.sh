#!/bin/bash

# Place this file in /usr/local/bin
# Run `chmod + x llama-server.sh` after placing the file
# Starts llama.cpp server


# Build command string
SERVER_BINARY="/usr/local/llama.cpp/build/bin/llama-server"
COMMAND="$SERVER_BINARY $LLAMA_SERVER_ARGS"

# Start server
echo "Running: $COMMAND"
$COMMAND
