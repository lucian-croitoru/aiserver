# GPU and Llama Server Configuration

This project provides a way to configure both NVIDIA GPU settings and Llama.cpp server using environment variables instead of hardcoded values.

## Files

### NVIDIA Settings
1. `nvidia-underclock.sh` - The script that applies NVIDIA GPU settings
2. `nvidia-underclock.service` - Systemd service file to run the script at boot
3. `nvidia-underclock.env` - Environment file containing NVIDIA configuration values

### Llama Server
4. `llama-server.sh` - The script that starts the Llama.cpp server
5. `llama-server.service` - Systemd service file to run the server at boot
6. `llama-server.env` - Environment file containing Llama server configuration values

## NVIDIA Environment Variables

The NVIDIA script uses the following environment variables:

- `NVIDIA_POWER_LIMIT` - Power limit in watts
- `NVIDIA_MEMORY_CLOCKS` - Memory clocks setting (format: min,max)
- `NVIDIA_GRAPHICS_CLOCKS` - Graphics clocks setting (format: min,max)

The script will only execute commands for variables that are set and non-empty. If a variable is not set or has an empty value (e.g., `NVIDIA_POWER_LIMIT=`), the corresponding command will be skipped.

## Llama Server Environment Variables

The Llama server script a single `LLAMA_SERVER_ARGS` variable in `/etc/llama-server.env` to pass all arguments for `llama.cpp`'s `llama-server`. Other `lama-server` environment variables can also be written. 

### Example args for llama-server.env
~~~
# DGGML_CUDA_FORCE_MMQ=1
# DGGML_CUDA_FORCE_CUBLAS=1
# GGML_CUDA_ENABLE_UNIFIED_MEMORY=1
CUDA_VISIBLE_DEVICES=0,1

LLAMA_SERVER_ARGS="-m /etc/models/Qwen3.6-35B-A3B-UD-Q8_K_XL_MTP.gguf \
  --mmproj /etc/models/Qwen3.6-35B-A3B-mmproj-F16.gguf \
  -ngl 999 \
  -sm layer \
  -ts 1,1 \
  -fa on \
  --no-mmap \
  --host 0.0.0.0 \
  --port 8111 \
  -ctk q8_0 \
  -ctv q8_0 \
  --ctx-size 262144 \
  --cont-batching \
  --threads 4 \
  --threads-batch 4 \
  --spec-type draft-mtp,ngram-mod \
  --spec-draft-n-max 2 \
  --temp 0.6 \
  --top-p 0.9 \
  -b 1024 \
  -ub 256 \
  --repeat-penalty 1.05 \
  --presence-penalty 1.3"
~~~

## Installation

Run `chmod +x setup-aiserver`
Modify the `nvidia-underclock.env` and / or `llama-server.env` files in `/etc` with your desired values.
After installation, both services will automatically apply their respective settings at boot time.

### Other notes
In `/etc/fstab` add `//[SERVER_NAME]/[SHARE_NAME] /mnt/models cifs guest` as a SMB share to copy models from
