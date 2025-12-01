#!/bin/bash

# Place this file in /usr/local/bin
# Run `chmod + x nvidia-underclock.sh` after placing the file
# Sets NVIDIA GPU powerlimit and clock settings per GPU type

# Sleep 10 seconds, wait for drivers to fully load
sleep 10

# Enable persistence mode
echo "Enabling persistence mode..."
nvidia-smi -pm 1

# Function to get GPU type from name
get_gpu_type() {
    local gpu_name="$1"
    if [[ "$gpu_name" == *"RTX 3090"* ]]; then
        echo "RTX3090"
    elif [[ "$gpu_name" == *"RTX 2080 Ti"* ]]; then
        echo "RTX2080TI"
    #else
        # For unknown GPU types, use the full name as identifier
    #    echo "${gpu_name// /}" | tr '[:upper:]' '[:lower:]'
    fi
}

# Get all GPUs with their index and name
echo "Detecting GPUs..."
gpu_list=$(nvidia-smi --query-gpu=index,name --format=csv,noheader)

# Create associative arrays to store settings by GPU type
declare -A power_limits
declare -A memory_clocks
declare -A graphics_clocks

# Process each GPU to build type-based settings
while IFS=',' read -r gpu_index gpu_name; do
    # Trim whitespace
    gpu_index=$(echo "$gpu_index" | xargs)
    gpu_name=$(echo "$gpu_name" | xargs)
    
    # Get GPU type
    gpu_type=$(get_gpu_type "$gpu_name")
    
    # Build settings arrays for this GPU type if not already set
    # Create variable names for power limit, memory clocks, and graphics clocks
    power_limit_var="NVIDIA_POWER_LIMIT_${gpu_type}"
    memory_clocks_var="NVIDIA_MEMORY_CLOCKS_${gpu_type}"
    graphics_clocks_var="NVIDIA_GRAPHICS_CLOCKS_${gpu_type}"
    
    # Use indirect expansion to get values from environment variables
    if [[ -z "${power_limits[$gpu_type]}" ]] && [[ -n "${!power_limit_var}" ]]; then
        power_limits[$gpu_type]="${!power_limit_var}"
    fi
    
    if [[ -z "${memory_clocks[$gpu_type]}" ]] && [[ -n "${!memory_clocks_var}" ]]; then
        memory_clocks[$gpu_type]="${!memory_clocks_var}"
    fi
    
    if [[ -z "${graphics_clocks[$gpu_type]}" ]] && [[ -n "${!graphics_clocks_var}" ]]; then
        graphics_clocks[$gpu_type]="${!graphics_clocks_var}"
    fi
    
    # Apply settings to this specific GPU
    echo "Applying settings to GPU $gpu_index ($gpu_name) - Type: $gpu_type"
    
    # Apply power limit
    if [[ -n "${power_limits[$gpu_type]}" ]]; then
        echo "Setting power limit to ${power_limits[$gpu_type]} W for GPU $gpu_index..."
        nvidia-smi -pl ${power_limits[$gpu_type]} -i $gpu_index
    else
        echo "Skipping power limit setting for GPU $gpu_index (no settings for type $gpu_type)"
    fi

    # Apply memory clocks
    if [[ -n "${memory_clocks[$gpu_type]}" ]]; then
        echo "Setting memory clocks to ${memory_clocks[$gpu_type]} for GPU $gpu_index..."
        nvidia-smi -lmc ${memory_clocks[$gpu_type]} -i $gpu_index
    else
        echo "Skipping memory clock setting for GPU $gpu_index (no settings for type $gpu_type)"
    fi

    # Apply graphics clocks
    if [[ -n "${graphics_clocks[$gpu_type]}" ]]; then
        echo "Setting graphics clocks to ${graphics_clocks[$gpu_type]} for GPU $gpu_index..."
        nvidia-smi -lgc ${graphics_clocks[$gpu_type]} -i $gpu_index
    else
        echo "Skipping graphics clock setting for GPU $gpu_index (no settings for type $gpu_type)"
    fi
    
done <<< "$gpu_list"

echo "All GPU settings applied successfully."
