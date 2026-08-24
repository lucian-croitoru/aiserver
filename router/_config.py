import asyncio
import logging
import os


# ============================================================
# Logging
# ============================================================

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
)

logging.basicConfig(
    level=LOG_LEVEL,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("agent-router")


# ============================================================
# LLM configuration
# ============================================================

# Instances of llama-server
TRIAGER_URL = os.getenv(
    "TRIAGER_URL",
    "http://127.0.0.1:8114/",
)

WORKER_URL = os.getenv(
    "WORKER_URL",
    "http://127.0.0.1:8113/",
)

BRAIN_URL = os.getenv(
    "BRAIN_URL",
    "http://127.0.0.1:8112/",
)


# Model names reported to llama-server

TRIAGER_MODEL = os.getenv(
    "TRIAGER_MODEL",
    "qwen3.5-4b",
)

WORKER_MODEL = os.getenv(
    "WORKER_MODEL",
    "qwen3.5-9b",
)

BRAIN_MODEL = os.getenv(
    "BRAIN_MODEL",
    "qwen3.8-27b",
)


# Requests above this input-token count bypass the TRIAGER
# classifier and go directly to the BRAIN.

ROUTING_LIMIT = int(
    os.getenv("ROUTING_LIMIT", 48000)
)


# ============================================================
# Timeouts
# ============================================================

# Timeout for token count endpoint

TOKEN_TIMEOUT = int(
    os.getenv("TOKEN_TIMEOUT", 60)
)


# Timeout for any inference endpoint

INFERENCE_TIMEOUT = int(
    os.getenv("INFERENCE_TIMEOUT", 1800)
)


# ============================================================
# Concurrency
# ============================================================

# Maximum number of simultaneous inference requests handled
# by each model.

TRIAGER_CONCURRENCY = int(
    os.getenv("TRIAGER_CONCURRENCY", 2)
)

WORKER_CONCURRENCY = int(
    os.getenv("WORKER_CONCURRENCY", 2)
)

BRAIN_CONCURRENCY = int(
    os.getenv("BRAIN_CONCURRENCY", 1)
)


triager_semaphore = asyncio.Semaphore(
    TRIAGER_CONCURRENCY
)

worker_semaphore = asyncio.Semaphore(
    WORKER_CONCURRENCY
)

brain_semaphore = asyncio.Semaphore(
    BRAIN_CONCURRENCY
)


# ============================================================
# FastAPI router configuration
# ============================================================

# This acts as an OpenAI-compatible API.
# Tools see this as a standard LLM.

ROUTER_HOST = os.getenv(
    "ROUTER_HOST",
    "0.0.0.0",
)

ROUTER_PORT = int(
    os.getenv(
        "ROUTER_PORT",
        8111,
    )
)