# aiserver

Deploy and manage llama.cpp inference servers on home GPU servers using
environment files and systemd. Also includes an experimental SDXL image
generation API and a reference script for Unraid GPU passthrough.

This repo started as an experimental project for my own homelab and is
intended primarily for personal use. The goal is simple: help local AI enthusiasts get
their inference engines running quickly with minimal fuss. Nothing too fancy —
just the setup that works for me, shared in case it saves you some time.

## How it works

- `nvidia-underclock.service` — applies per-GPU-type power limits and clock
  ranges at boot, driven by `/etc/nvidia-underclock.env`.
- `llama-inference@.service` — a systemd **template unit**: one instance per
  config file in `/etc/llama-inference/<name>.env`.
- `llama-inference-generator` — a systemd generator that auto-enables an
  instance for every `.env` file it finds, on boot and on every
  `systemctl daemon-reload`. The running set of instances always matches the
  set of config files.

### Managing instances

```bash
# one instance
systemctl start   llama-inference@<name>.service
systemctl restart llama-inference@<name>.service
systemctl stop    llama-inference@<name>.service

# all instances
systemctl restart 'llama-inference@*.service'

# add an instance: put a config at /etc/llama-inference/<name>.env, then
sudo systemctl daemon-reload

# remove an instance: delete the .env file, then
sudo systemctl daemon-reload
```

Instances restart automatically on failure (`Restart=on-failure`).

## Installation

Run as root (the script calls `apt` and `systemctl` directly):

```bash
chmod +x setup-aiserver.sh
./setup-aiserver.sh
```

The script:

1. Installs build dependencies and the NVIDIA driver.
2. Clones and compiles `llama.cpp` with CUDA into `/usr/local/llama.cpp`.
3. Installs the systemd units, the generator, the helper scripts
   (`/usr/local/bin`), and the default configs.

### Hardcoded values you may need to change

- **NVIDIA driver** — `setup-aiserver.sh` installs `nvidia-driver-580`.
  Change the package name to the driver you want.
- **CUDA architectures** — the build is compiled for `75;86` (Turing, Ampere).
  Add your GPU's architecture to `CMAKE_CUDA_ARCHITECTURES` in
  `setup-aiserver.sh` (e.g. `89` for Ada, `90` for Hopper).
- **llama.cpp version** — the script clones `master` and rebuilds on every
  run. Pin a release tag if you want reproducible installs.

## Configuration

### `/etc/llama-inference/<name>.env`

One file per inference instance. The file is loaded as a systemd
`EnvironmentFile`; everything in `LLAMA_SERVER_ARGS` is passed to
`llama-server` as-is. `LLAMA_SERVER_DELAY` (seconds) is an optional per-
instance startup delay applied via `ExecStartPre`, useful for staggering
model loads across instances.

> **Note:** a fresh install creates `/etc/llama-inference/default.env` with a
> placeholder model path. It defines a real instance, so you must either edit
> it with your own model and settings, or replace it with a real config.
> Until you do, `llama-inference@default` will fail to start.
>
> See `examples/` for ready-made configs you can copy and adapt.

### `/etc/nvidia-underclock.env`

Per-GPU-type power limits and clock ranges, e.g.:

```
NVIDIA_POWER_LIMIT_RTX3090=250
NVIDIA_MEMORY_CLOCKS_RTX3090=405,9501
NVIDIA_GRAPHICS_CLOCKS_RTX3090=210,1800
```

Leave a value blank to skip it. The file's comments list the supported GPU
types and how to add more.

## Security notes

- The default and example configs bind `llama-server` to `--host 0.0.0.0`
  with **no authentication**. That is fine on a trusted home LAN, but do not
  expose these ports to the internet — anyone who can reach them can use your
  GPU and see whatever the model is asked.
- The SDXL API below is the same story: no auth, all interfaces.

## Models over CIFS (optional)

If you keep your GGUF models on a network share, mount it in `/etc/fstab`:

```
//<server>/<share> /mnt/models cifs guest 0 0
```

and point `LLAMA_SERVER_ARGS` at `/mnt/models/...` instead of
`/etc/models/...`.

## SDXL image generation API (experimental, manual setup)

`sdxl/` contains a minimal, work-in-progress OpenAI-compatible image
generation API (FastAPI + diffusers). It is **not** installed by
`setup-aiserver.sh`; set it up manually if you want it:

```bash
source venv.sh                        # builds .venv, installs requirements.txt
sudo cp lib/systemd/sdxl-server.service /etc/systemd/system/
sudo cp lib/configs/sdxl-server.env /etc/sdxl-server.env
sudo systemctl daemon-reload
sudo systemctl enable --now sdxl-server
```

- Listens on `0.0.0.0:8115`; endpoint `POST /v1/images/generations`.
- `sdxl/models.py` hardcodes the base model to `cuda:2` and the refiner to
  `cuda:3` — change the `DESTINATION` in each class to match your setup.
- `sdxl-server.sh` and `sdxl-server.env` assume the repo lives in `~/aiserver`
  with the venv in `~/aiserver/.venv`; adjust the paths if yours is elsewhere.
- See `sdxl/README.md` for the API reference.

## Unraid GPU passthrough (reference)

`host_lib/update_vm_gpus.sh` is a reference script for Unraid users: it
rewrites a libvirt VM's XML to pass through every NVIDIA RTX GPU it finds on
the host, using the PCI addresses assigned at boot. The GPU name list, VM XML
path, and ROM folder are hardcoded at the top of the script — adapt them to
your setup.
