#!/bin/bash

# Place this file in /usr/local/bin
# Run `chmod + x llama-server.sh` after placing the file
# Starts llama.cpp server


REQUIRED_VARIABLES=("RUNTIME" "HOST" "PORT" "MODELS_DIR" "MODEL" "CONTEXT_LENGTH")

# Function to check if variables are set and non-empty
check_variables() {
    local missing_vars=()
    
    # Loop through all passed arguments (variable names)
    for var_name in "$@"; do
        # Check if variable is set and non-empty
        if [[ -z "${!var_name}" ]]; then
            missing_vars+=("$var_name")
        fi
    done
    
    # If we found missing variables, print error and exit
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo "ERROR: The following variables are missing or empty:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
}
check_variables "${REQUIRED_VARIABLES[@]}"


# Test for existing model file
if ! test -f "$MODELS_DIR/$MODEL"; then
  echo "ERROR: The path [$MODELS_DIR/$MODEL] does not exist."
  exit 1
fi


# Test for valid RUNTIME variable
if [$RUNTIME != "vulkan"] && [$RUNTIME != "cuda"]; then
  echo "ERROR: Invalid value for RUNTIME: '$RUNTIME'. The accepted values for RUNTIME are 'vulkan' and 'cuda'."
  exit 1
fi


# Add --mmproj argument and value, if provided
MMPROJ_ARG=""
if [ -n "$MMPROJ" ]; then
    # Do nothing
else
    MMPROJ_ARG="--mmproj $MODELS_DIR/$MMPROJ"
fi


# Build command string
SERVER_BINARY="/usr/local/llama-cpp-$RUNTIME/build/bin/llama-server"
COMMAND="$SERVER_BINARY --model $MODELS_DIR/$MODEL --host $HOST --port $PORT -ngl 100 -fa on -c $CONTEXT_LENGTH $MMPROJ_ARG"

# Start server
echo "Running: $COMMAND"
$COMMAND
