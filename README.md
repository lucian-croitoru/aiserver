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

The Llama server script uses the following environment variables:

- `RUNTIME` - Runtime type (either 'vulkan' or 'cuda')
- `MODEL` - Model file name (default: (empty))
- `CONTEXT_LENGTH` - Context length (default: 4096)
- `HOST` - Host address (default: 0.0.0.0)
- `PORT` - Port number (default: 8080)
- `MODELS_DIR` - Local models directory (default: /etc/models)
- `MMPROJ` - (Optional): .mmproj file name (default: (empty))

## Llama Server Features

- **Runtime selection**: Supports both 'vulkan' and 'cuda' runtimes
- **Flexible configuration**: All server parameters can be customized via environment variables
- **Default values**: Safe defaults are provided for all parameters
- **Environment file support**: Configuration loaded from external .env files
- **Model validation**: Checks if the specified model file exists before starting the server
- **Runtime validation**: Ensures the RUNTIME variable is set to either 'vulkan' or 'cuda'
- **Required variables**: All configuration variables must be set and non-empty


## Installation

Run `chmod +x setup-aiserver`
Modify the `nvidia-underclock.env` and / or `llama-server.env` files in `/etc` with your desired values.
Ensure that the model file (`MODEL`) specified in `llama-server.env` exists in the `MODELS_DIR` directory.
After installation, both services will automatically apply their respective settings at boot time.
