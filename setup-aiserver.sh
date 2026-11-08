#!/bin/bash

################################################
#                                              #
#   Installation script for llama.cpp server   #
#                                              #
################################################

# Exit immediately on error
set -e

# Define global variables
apt install wget nvidia-driver-580 nvidia-cuda-toolkit nvtop cifs-utils cmake build-essential libnccl-dev libssl-dev python3-pip python3-dev python3-venv

RESET_NVIDIA_UNDERCLOCK_CONFIG=0
# Default to reset (fresh install uses repo defaults and does not auto-start)
RESET_LLAMA_INFERENCE_CONFIG=1
INSTALL_DIR="/usr/local"
NVIDIA_UNDERCLOCK_SERVICE="nvidia-underclock"
LLAMA_INFERENCE_SERVICE="llama-inference"
LLAMA_INFERENCE_CONFIG_DIR="/etc/llama-inference"
LLAMA_SERVER_SCRIPT="llama-server"


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

### Install llama.cpp

# Cleanup folders
echo "Installing $LLAMA_INFERENCE_SERVICE..."
rm -rf $INSTALL_DIR/llama.cpp
cd $INSTALL_DIR

# Download release
echo "Downloading latest release..."
git clone https://github.com/ggml-org/llama.cpp.git
cd $INSTALL_DIR/llama.cpp

echo "Compiling..."
cmake -B build \
  -DGGML_CUDA=ON \
  -DGGML_NCCL=ON \
  -DGGML_CUDA_FA=ON \
  -DGGML_CUDA_P2P=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA_FORCE_MMQ=OFF \
  -DGGML_CUDA_FORCE_CUBLAS=OFF \
  -DCMAKE_CUDA_ARCHITECTURES="75;86"

# 75 = Turing, 86 = Ampere
echo "Done."

echo "Building..."
cmake --build build -j
echo "Done."


# Setup services
echo "Setting up services..."
if [ $RESET_NVIDIA_UNDERCLOCK_CONFIG -gt 0 ]; then
  cp -f $PWD/lib/configs/$NVIDIA_UNDERCLOCK_SERVICE.env /etc/$NVIDIA_UNDERCLOCK_SERVICE.env
fi

mkdir -p $LLAMA_INFERENCE_CONFIG_DIR
if [ $RESET_LLAMA_INFERENCE_CONFIG -gt 0 ]; then
  cp -f $PWD/lib/configs/llama-inference/*.env $LLAMA_INFERENCE_CONFIG_DIR/
else
  # Install repo defaults for instances that have no config yet
  for env_file in $PWD/lib/configs/llama-inference/*.env; do
      name=$(basename "$env_file")
      [ -f "$LLAMA_INFERENCE_CONFIG_DIR/$name" ] || cp -f "$env_file" "$LLAMA_INFERENCE_CONFIG_DIR/$name"
  done
fi

cp $PWD/lib/scripts/*.sh $INSTALL_DIR/bin
cp $PWD/lib/systemd/nvidia-underclock.service /etc/systemd/system
cp $PWD/lib/systemd/llama-inference@.service /etc/systemd/system
mkdir -p /etc/systemd/system-generators
cp $PWD/lib/systemd/llama-inference-generator /etc/systemd/system-generators/
chmod +x $INSTALL_DIR/bin/$NVIDIA_UNDERCLOCK_SERVICE.sh
chmod +x $INSTALL_DIR/bin/$LLAMA_SERVER_SCRIPT.sh
chmod +x /etc/systemd/system-generators/llama-inference-generator

systemctl daemon-reload
systemctl enable $NVIDIA_UNDERCLOCK_SERVICE.service
# llama-inference instances are auto-enabled by the generator on daemon-reload

# Sanity check: the generator must have enabled at least one instance
if ! systemctl list-unit-files "llama-inference@*.service" | grep -q "llama-inference@"; then
    echo "ERROR: no $LLAMA_INFERENCE_SERVICE instances enabled. Check $LLAMA_INFERENCE_CONFIG_DIR/*.env and /etc/systemd/system-generators/llama-inference-generator."
    exit 1
fi


# Restart services
echo "Restarting $NVIDIA_UNDERCLOCK_SERVICE.service..."
systemctl restart $NVIDIA_UNDERCLOCK_SERVICE.service
echo "[INFO]: Edit /etc/$NVIDIA_UNDERCLOCK_SERVICE.env to tweak NVIDIA GPU settings."
echo "[INFO]: Run 'sudo systemctl restart $NVIDIA_UNDERCLOCK_SERVICE.service' for the settings to take effect."

if [ $RESET_LLAMA_INFERENCE_CONFIG -gt 0 ]; then
  echo "[WARNING]: $LLAMA_INFERENCE_SERVICE instances were not started because the configuration was reset."
else
  if ls $LLAMA_INFERENCE_CONFIG_DIR/*.env &>/dev/null; then
    echo "Starting $LLAMA_INFERENCE_SERVICE instances..."
    systemctl start 'llama-inference@*.service'
  fi
fi
echo "[INFO]: Edit $LLAMA_INFERENCE_CONFIG_DIR/<name>.env to tweak a specific llama server instance."
echo "[INFO]: Add $LLAMA_INFERENCE_CONFIG_DIR/<name>.env and run 'sudo systemctl daemon-reload' to add an instance."
echo "[INFO]: Run 'sudo systemctl restart llama-inference@<name>.service' to restart a single instance."
echo "[INFO]: Run 'sudo systemctl restart llama-inference@*.service' to restart all instances."


# Finish
echo "Finished."
