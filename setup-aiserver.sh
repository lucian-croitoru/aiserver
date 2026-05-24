#!/bin/bash

################################################
#                                              #
#   Installation script for llama.cpp server   #
#                                              #
################################################

# Exit immediately on error
set -e

# Define global variables
REQUIREMENTS=(wget nvidia-driver-580 nvidia-cuda-toolkit nvtop cifs-utils)

RESET_NVIDIA_UNDERCLOCK_CONFIG=0
RESET_LLAMA_SERVER_CONFIG=0
INSTALL_DIR="/usr/local"
NVIDIA_UNDERCLOCK_SERVICE="nvidia-underclock"
LLAMA_SERVER_SERVICE="llama-server"

RELEASE="b9284"
LLAMA_CPP_VULKAN="llama-$RELEASE-bin-ubuntu-vulkan-x64.tar.gz"


# Set a log prefix for every internal `echo` command
LOG_PREFIX="[setup-aiserver] "
echo() {
  builtin echo "$LOG_PREFIX $*"
}

echo "Starting..."
echo "Checking for old installations..."

# Check for existing nvidia-underclock config
if test -f "/etc/$NVIDIA_UNDERCLOCK_SERVICE.env"; then
  echo "WARNING: existing configuration found for [$NVIDIA_UNDERCLOCK_SERVICE.service]"
  while true; do
    read -p "$LOG_PREFIX Do you want to 'keep' or 'reset'?: " response
    case $response in
      [Kk][Ee][Ee][Pp])
        # Do nothing
        break
        ;;
      [Rr][Ee][Ss][Ee][Tt])
        # Flag reset settings
        RESET_NVIDIA_UNDERCLOCK_CONFIG=1
        break
        ;;
      *)
        echo "Please answer with 'keep' or 'reset'."
        ;;
    esac
  done
else
  RESET_NVIDIA_UNDERCLOCK_CONFIG=1
fi

# Check for existing llama-server config
if test -f "/etc/$LLAMA_SERVER_SERVICE.env"; then
  echo "WARNING: existing configuration found for [$LLAMA_SERVER_SERVICE.service]"
  while true; do
    read -p "$LOG_PREFIX Do you want to 'keep' or 'reset'?: " response
    case $response in
      [Kk][Ee][Ee][Pp])
        # Do nothing
        break
        ;;
      [Rr][Ee][Ss][Ee][Tt])
        # Flag reset settings
        RESET_LLAMA_SERVER_CONFIG=1
        break
        ;;
      *)
        echo "Please answer with 'keep' or 'reset'."
        ;;
    esac
  done
else
  RESET_LLAMA_SERVER_CONFIG=1
fi


# Install minimal requirements
echo "Checking requirements..."
for pkg in "${REQUIREMENTS[@]}"; do
    if [ ! dpkg -s "$pkg" &>/dev/null ]; then
        echo "Installing required package: $pkg"
        apt-get install -y "$pkg"
    fi
done


### Install llama.cpp
# Stop service if running
if systemctl cat "$LLAMA_SERVER_SERVICE.service" &>/dev/null; then
    if systemctl is-active --quiet "$LLAMA_SERVER_SERVICE.service"; then
        # Service exists and is running: stop the service
        echo "Stopping $LLAMA_SERVER_SERVICE.service..."
        systemctl stop "$LLAMA_SERVER_SERVICE".service
    fi
fi

# Cleanup folders
echo "Installing $LLAMA_SERVER_SERVICE..."
rm -rf $INSTALL_DIR/llama-cpp-vulkan
mkdir $INSTALL_DIR/llama-cpp-vulkan

# Download release
echo "Downloading Vulkan release..."
wget -O $INSTALL_DIR/llama-cpp-vulkan/$LLAMA_CPP_VULKAN "https://github.com/ggml-org/llama.cpp/releases/download/$RELEASE/$LLAMA_CPP_VULKAN"
tar -xzvf $INSTALL_DIR/llama-cpp-vulkan/$LLAMA_CPP_VULKAN -C $INSTALL_DIR/llama-cpp-vulkan
mv $INSTALL_DIR/llama-cpp-vulkan/llama-$RELEASE $INSTALL_DIR/llama-cpp-vulkan/bin

# Setup services
echo "Setting up services..."
if [ $RESET_NVIDIA_UNDERCLOCK_CONFIG -gt 0 ]; then
  cp -f lib/$NVIDIA_UNDERCLOCK_SERVICE.env /etc/$NVIDIA_UNDERCLOCK_SERVICE.env
fi

if [ $RESET_LLAMA_SERVER_CONFIG -gt 0 ]; then
  cp -f lib/$LLAMA_SERVER_SERVICE.env /etc/$LLAMA_SERVER_SERVICE.env
fi

cp lib/*.sh $INSTALL_DIR/bin
cp lib/*.service /etc/systemd/system
chmod +x $INSTALL_DIR/bin/$NVIDIA_UNDERCLOCK_SERVICE.sh
chmod +x $INSTALL_DIR/bin/$LLAMA_SERVER_SERVICE.sh
systemctl daemon-reload
systemctl enable $NVIDIA_UNDERCLOCK_SERVICE.service
systemctl enable $LLAMA_SERVER_SERVICE.service


# Restart services
echo "Restarting $NVIDIA_UNDERCLOCK_SERVICE.service..."
systemctl restart $NVIDIA_UNDERCLOCK_SERVICE.service
echo "[INFO]: Edit /etc/$NVIDIA_UNDERCLOCK_SERVICE.env to tweak NVIDIA GPU settings."
echo "[INFO]: Run 'sudo systemctl restart $NVIDIA_UNDERCLOCK_SERVICE.service' for the settings to take effect."

if [ $RESET_LLAMA_SERVER_CONFIG -gt 0 ]; then
  echo "[WARNING]: $LLAMA_SERVER_SERVICE.service was not started because the configuration was reset."
else
  echo "Restarting $LLAMA_SERVER_SERVICE.service..."
  systemctl restart $LLAMA_SERVER_SERVICE.service
fi
echo "[INFO]: Edit /etc/$LLAMA_SERVER_SERVICE.env to specify the model file path and other settings for the llama server."
echo "[INFO]: Run 'sudo systemctl restart $LLAMA_SERVER_SERVICE.service' for the settings to take effect."


# Finish
echo "Finished."
