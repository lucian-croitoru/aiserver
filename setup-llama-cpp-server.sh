#!/bin/bash

# Update packages and install requirements
apt update && apt upgrade -y
# Install minimal requirements (vulkan)
apt-get install -y wget unzip nvidia-driver-580 nvidia-cuda-toolkit nvtop cifs-utils
# Install additional requirements (cuda)
# TODO...

# Get latest release tag and build URL and filename variable
RELEASE="b6816"
LLAMA_CPP_VULKAN="llama-$RELEASE-bin-ubuntu-vulkan-x64.zip"
LLAMA_CPP_CUDA="llama-$RELEASE-bin-ubuntu-x64.zip"


# Clean up old installation
echo "Removing any old installations..."
rm -rf /usr/local/llama-cpp-vulkan
rm -rf /usr/local/llama-cpp-cuda
systemctl stop nvidia-settings.service
systemctl stop llama-server.service

# Create folders
echo "Creating folders..."
mkdir /usr/local/llama-cpp-vulkan
mkdir /usr/local/llama-cpp-cuda
mkdir /etc/models

# Download release
echo "Downloading CUDA release..."
wget -O /usr/local/llama-cpp-cuda/$LLAMA_CPP_CUDA "https://github.com/ggml-org/llama.cpp/releases/download/$RELEASE/$LLAMA_CPP_CUDA"
unzip /usr/local/llama-cpp-cuda/$LLAMA_CPP_CUDA -d /usr/local/llama-cpp-cuda

echo "Downloading Vulkan release..."
wget -O /usr/local/llama-cpp-vulkan/$LLAMA_CPP_VULKAN "https://github.com/ggml-org/llama.cpp/releases/download/$RELEASE/$LLAMA_CPP_VULKAN"
unzip /usr/local/llama-cpp-vulkan/$LLAMA_CPP_VULKAN -d /usr/local/llama-cpp-vulkan

# Setup services
echo "Setting up services..."
cp lib/*.env /etc
cp lib/*.sh /usr/local/bin
cp lib/*.service /etc/systemd/system
chmod +x /usr/local/bin/nvidia-settings.sh
chmod +x /usr/local/bin/llama-server.sh

systemctl daemon-reload
systemctl enable nvidia-settings.service
systemctl enable llama-server.service
systemctl start nvidia-settings.service

# Finish
echo "Done."
echo "Edit /etc/nvidia-settings.env to tweak NVIDIA GPU settings."
echo "Run 'sudo systemctl restart nvidia-settings.service' for the settings to take effect."
echo "Edit /etc/llama-server.env to specify the model and other settings."
echo "Make sure the model file exists in /etc/models."
echo "Run 'sudo systemctl restart llama-server.service'."
