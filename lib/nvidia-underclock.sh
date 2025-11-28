#!/bin/bash

# Place this file in /usr/local/bin
# Run `chmod + x nvidia-underclock.sh` after placing the file
# Sets global NVIDIA GPU powerlimit and clock settings

# Sleep 30 seconds, wait for drivers to fully load
sleep 30

# Enable mersistence mode
echo "Enabling persistence mode..."
nvidia-smi -pm 1

# Set power limit
if [ -n "$NVIDIA_POWER_LIMIT" ]; then
    echo "Setting power limit to $NVIDIA_POWER_LIMIT W..."
    nvidia-smi -pl $NVIDIA_POWER_LIMIT
else
    echo "Skipping power limit setting (no NVIDIA_POWER_LIMIT specified or value is empty)"
fi

# Set min/max memory clocks
if [ -n "$NVIDIA_MEMORY_CLOCKS" ]; then
    echo "Setting memory clocks to $NVIDIA_MEMORY_CLOCKS..."
    nvidia-smi -lmc $NVIDIA_MEMORY_CLOCKS
else
    echo "Skipping memory clock setting (no NVIDIA_MEMORY_CLOCKS specified or value is empty)"
fi

# Set min/max graphics clocks
if [ -n "$NVIDIA_GRAPHICS_CLOCKS" ]; then
    echo "Setting graphics clocks to $NVIDIA_GRAPHICS_CLOCKS..."
    nvidia-smi -lgc $NVIDIA_GRAPHICS_CLOCKS
else
    echo "Skipping graphics clock setting (no NVIDIA_GRAPHICS_CLOCKS specified or value is empty)"
fi
