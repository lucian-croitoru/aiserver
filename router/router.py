#!/usr/bin/env python3

import asyncio
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from _config import (
    logger,
    triager_semaphore,
    worker_semaphore,
    brain_semaphore,
    TOKEN_TIMEOUT,
    INFERENCE_TIMEOUT,
    ROUTING_LIMIT,
    TRIAGER_CONCURRENCY,
    WORKER_CONCURRENCY,
    BRAIN_CONCURRENCY,
    TRIAGER_URL,
    TRIAGER_MODEL,
    WORKER_URL,
    WORKER_MODEL,
    BRAIN_URL,
    BRAIN_MODEL,
    ROUTER_HOST,
    ROUTER_PORT,
)

from _system_prompts import TRIAGER_SYSTEM_PROMPT


# ============================================================
# Application lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application-wide resources.

    Resources created before `yield` are initialized during
    application startup.

    Resources cleaned up after `yield` are released during
    application shutdown.
    """

    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=10.0,
            read=INFERENCE_TIMEOUT,
            write=INFERENCE_TIMEOUT,
            pool=INFERENCE_TIMEOUT,
        )
    )

    logger.info(
        "Router started | "
        "routing_limit=%d | "
        "triager_concurrency=%d | "
        "worker_concurrency=%d | "
        "brain_concurrency=%d",
        ROUTING_LIMIT,
        TRIAGER_CONCURRENCY,
        WORKER_CONCURRENCY,
        BRAIN_CONCURRENCY,
    )

    try:
        yield

    finally:
        await app.state.http_client.aclose()
        logger.info("Router stopped")


app = FastAPI(lifespan=lifespan)


def get_client(request: Request) -> httpx.AsyncClient:
    """
    Return the application-wide HTTP client.

    The client is created during the FastAPI lifespan startup
    phase and closed during shutdown.
    """

    client = getattr(request.app.state, "http_client", None)

    if client is None:
        raise RuntimeError(
            "HTTP client has not been initialized"
        )

    return client


# ============================================================
# Error helper
# ============================================================

def error_response(
    message: str,
    status_code: int = 500,
):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": "router_error",
                "param": None,
                "code": None,
            }
        },
    )


# ============================================================
# Token counting
# ============================================================

async def count_input_tokens(
    request: Request,
    messages: list,
) -> int:
    """
    Ask llama-server to count the input tokens.

    This is intentionally NOT protected by the model inference
    semaphores. Tokenization is separate from model generation
    concurrency.
    """

    url = (
        TRIAGER_URL.rstrip("/")
        + "/chat/completions/input_tokens"
    )

    payload = {
        "model": TRIAGER_MODEL,
        "messages": messages,
    }

    start = time.perf_counter()

    response = await get_client(request).post(
        url,
        json=payload,
        timeout=TOKEN_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()

    tokens = int(
        data["input_tokens"]
    )

    elapsed = time.perf_counter() - start

    logger.debug(
        "Tokenized %d tokens in %.3fs",
        tokens,
        elapsed,
    )

    return tokens


# ============================================================
# Generic llama-server request
# ============================================================

async def call_model(
    request: Request,
    base_url: str,
    model: str,
    messages: list,
    *,
    semaphore: asyncio.Semaphore,
    model_name: str,
    stream: bool,
    endpoint: str = "/chat/completions",
    **parameters,
):
    """
    Send one request to llama-server.

    Non-streaming requests are fully read by httpx and returned
    as a normal Response.

    Streaming requests are handled separately by stream_model().
    """

    # --------------------------------------------------------
    # Non-streaming request
    # --------------------------------------------------------

    if not stream:

        async with semaphore:

            logger.debug(
                "%s inference slot acquired",
                model_name,
            )

            url = (
                base_url.rstrip("/")
                + endpoint
            )

            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
            }

            # Preserve all OpenAI-compatible generation parameters.
            payload.update({
                key: value
                for key, value in parameters.items()
                if value is not None
            })

            start = time.perf_counter()

            try:

                response = await get_client(request).post(
                    url,
                    json=payload,
                    timeout=INFERENCE_TIMEOUT,
                )

                elapsed = (
                    time.perf_counter() - start
                )

                logger.debug(
                    "%s request completed in %.3fs",
                    model_name,
                    elapsed,
                )

                return response

            finally:

                logger.debug(
                    "%s inference slot released",
                    model_name,
                )


# ============================================================
# Streaming llama-server request
# ============================================================

async def stream_model(
    request: Request,
    base_url: str,
    model: str,
    messages: list,
    *,
    semaphore: asyncio.Semaphore,
    model_name: str,
    endpoint: str = "/chat/completions",
    **parameters,
):
    """
    Open a streaming request to llama-server.

    IMPORTANT:

    httpx.AsyncClient.post() is deliberately NOT used here.

    Instead, we create and send an httpx request with
    stream=True. This causes httpx to return as soon as the
    downstream response headers are available, without reading
    the response body.

    The returned response therefore remains connected to the
    llama-server stream.

    The inference semaphore is intentionally acquired here and
    remains held until the caller has received the entire
    downstream stream or disconnects.
    """

    await semaphore.acquire()

    logger.debug(
        "%s streaming inference slot acquired",
        model_name,
    )

    url = (
        base_url.rstrip("/")
        + endpoint
    )

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    # Preserve all OpenAI-compatible generation parameters.
    payload.update({
        key: value
        for key, value in parameters.items()
        if value is not None
    })

    client = get_client(request)

    start = time.perf_counter()

    try:

        downstream_request = client.build_request(
            "POST",
            url,
            json=payload,
        )

        # ----------------------------------------------------
        # CRITICAL:
        #
        # stream=True means the response body is NOT buffered.
        # httpx returns once the downstream response headers
        # arrive, leaving the body open for aiter_bytes().
        # ----------------------------------------------------

        response = await client.send(
            downstream_request,
            stream=True,
        )

        elapsed = (
            time.perf_counter() - start
        )

        logger.debug(
            "%s streaming connection established in %.3fs",
            model_name,
            elapsed,
        )

        try:

            response.raise_for_status()

        except Exception:

            # We own this response because stream=True was used.
            await response.aclose()

            raise

        return response

    except BaseException:

        # The response was never successfully handed to the
        # StreamingResponse generator, so release the slot here.
        semaphore.release()

        logger.debug(
            "%s streaming inference slot released "
            "before streaming started",
            model_name,
        )

        raise


async def forward_stream(
    response: httpx.Response,
    *,
    semaphore: asyncio.Semaphore,
    model_name: str,
):
    """
    Transparently forward bytes from llama-server to the caller.

    No parsing, buffering, transformation, or reconstruction of
    SSE messages is performed.

    Whatever bytes llama-server sends are yielded directly to
    FastAPI, which sends them to the caller.
    """

    try:

        async for chunk in response.aiter_bytes():

            if chunk:
                yield chunk

    except asyncio.CancelledError:

        logger.debug(
            "%s streaming request cancelled by caller",
            model_name,
        )

        raise

    finally:

        await response.aclose()

        semaphore.release()

        logger.debug(
            "%s streaming inference slot released",
            model_name,
        )


# ============================================================
# Classification
# ============================================================

async def classify(
    request: Request,
    messages: list,
) -> str:

    triage_messages = [
        {
            "role": "system",
            "content": TRIAGER_SYSTEM_PROMPT,
        },
        *[
            msg
            for msg in messages
            if msg.get("role") == "user"
        ],
    ]

    response = await call_model(
        request,
        TRIAGER_URL,
        TRIAGER_MODEL,
        triage_messages,
        semaphore=triager_semaphore,
        model_name=TRIAGER_MODEL,
        stream=False,
        temperature=0.0,
    )

    response.raise_for_status()

    data = response.json()

    content = (
        data["choices"][0]["message"]
        .get("content", "")
    )

    classification = (
        content.strip().lower()
    )

    # Normal expected responses.
    if classification == "trivial":
        return "trivial"

    if classification == "complex":
        return "complex"

    # Be tolerant of accidental additional text.
    if "trivial" in classification:
        return "trivial"

    if "complex" in classification:
        return "complex"

    # Safety default:
    #
    # An uncertain classification should go to the BRAIN,
    # not the WORKER.
    logger.warning(
        "Unexpected triage output: %r; "
        "defaulting to complex",
        content,
    )

    return "complex"


# ============================================================
# Response forwarding
# ============================================================

async def forward_response(
    response: httpx.Response,
    *,
    route: str,
    input_tokens: int,
):
    """
    Convert llama-server's non-streaming response into an
    OpenAI-compatible FastAPI response.
    """

    if response.is_error:

        return JSONResponse(
            status_code=response.status_code,
            content=response.json(),
        )

    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
        headers={
            "X-Agent-Route": route,
            "X-Agent-Input-Tokens": str(
                input_tokens
            ),
        },
    )


# ============================================================
# Main OpenAI-compatible endpoint
# ============================================================

@app.post("/chat/completions")
@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
):
    request_id = str(uuid.uuid4())

    try:

        body = await request.json()

        messages = body.get(
            "messages"
        )

        if not isinstance(
            messages,
            list,
        ):

            return error_response(
                "messages must be an array",
                400,
            )

        if not messages:

            return error_response(
                "messages must not be empty",
                400,
            )

        stream = bool(
            body.get(
                "stream",
                False,
            )
        )

        # ----------------------------------------------------
        # Preserve all OpenAI-compatible parameters.
        # ----------------------------------------------------

        generation_parameters = dict(
            body
        )

        generation_parameters.pop(
            "model",
            None,
        )

        generation_parameters.pop(
            "messages",
            None,
        )

        generation_parameters.pop(
            "stream",
            None,
        )

        # ----------------------------------------------------
        # 1. Count input tokens
        # ----------------------------------------------------

        input_tokens = (
            await count_input_tokens(
                request,
                messages,
            )
        )

        logger.info(
            "[%s] input_tokens=%d",
            request_id,
            input_tokens,
        )

        # ----------------------------------------------------
        # 2. Long context → BRAIN
        # ----------------------------------------------------

        if input_tokens > ROUTING_LIMIT:

            route = f"{BRAIN_MODEL}-long-context"

            logger.info(
                "[%s] route=%s",
                request_id,
                route,
            )

            if stream:

                response = await stream_model(
                    request,
                    BRAIN_URL,
                    BRAIN_MODEL,
                    messages,
                    semaphore=brain_semaphore,
                    model_name=BRAIN_MODEL,
                    **generation_parameters,
                )

                return StreamingResponse(
                    forward_stream(
                        response,
                        semaphore=brain_semaphore,
                        model_name=BRAIN_MODEL,
                    ),
                    status_code=response.status_code,
                    media_type=(
                        "text/event-stream"
                    ),
                    headers={
                        "X-Agent-Route": route,
                        "X-Agent-Input-Tokens":
                            str(input_tokens),

                        # Prevent intermediary buffering.
                        "Cache-Control": "no-cache",
                        "X-Accel-Buffering": "no",
                    },
                )

            response = await call_model(
                request,
                BRAIN_URL,
                BRAIN_MODEL,
                messages,
                semaphore=brain_semaphore,
                model_name=BRAIN_MODEL,
                stream=False,
                **generation_parameters,
            )

            return await forward_response(
                response,
                route=route,
                input_tokens=input_tokens,
            )

        # ----------------------------------------------------
        # 3. ≤ threshold → TRIAGER
        # ----------------------------------------------------

        classification = (
            await classify(
                request,
                messages,
            )
        )

        logger.info(
            "[%s] classification=%s",
            request_id,
            classification,
        )

        # ----------------------------------------------------
        # 4. Trivial → WORKER
        # ----------------------------------------------------

        if classification == "trivial":

            route = f"{WORKER_MODEL}-trivial"

            logger.info(
                "[%s] route=%s",
                request_id,
                route,
            )

            if stream:

                response = await stream_model(
                    request,
                    WORKER_URL,
                    WORKER_MODEL,
                    messages,
                    semaphore=worker_semaphore,
                    model_name=WORKER_MODEL,
                    **generation_parameters,
                )

                return StreamingResponse(
                    forward_stream(
                        response,
                        semaphore=worker_semaphore,
                        model_name=WORKER_MODEL,
                    ),
                    status_code=response.status_code,
                    media_type=(
                        "text/event-stream"
                    ),
                    headers={
                        "X-Agent-Route": route,
                        "X-Agent-Input-Tokens":
                            str(input_tokens),

                        # Prevent intermediary buffering.
                        "Cache-Control": "no-cache",
                        "X-Accel-Buffering": "no",
                    },
                )

            response = await call_model(
                request,
                WORKER_URL,
                WORKER_MODEL,
                messages,
                semaphore=worker_semaphore,
                model_name=WORKER_MODEL,
                stream=False,
                **generation_parameters,
            )

        # ----------------------------------------------------
        # 5. Complex → BRAIN
        # ----------------------------------------------------

        else:

            route = f"{BRAIN_MODEL}-complex"

            logger.info(
                "[%s] route=%s",
                request_id,
                route,
            )

            if stream:

                response = await stream_model(
                    request,
                    BRAIN_URL,
                    BRAIN_MODEL,
                    messages,
                    semaphore=brain_semaphore,
                    model_name=BRAIN_MODEL,
                    **generation_parameters,
                )

                return StreamingResponse(
                    forward_stream(
                        response,
                        semaphore=brain_semaphore,
                        model_name=BRAIN_MODEL,
                    ),
                    status_code=response.status_code,
                    media_type=(
                        "text/event-stream"
                    ),
                    headers={
                        "X-Agent-Route": route,
                        "X-Agent-Input-Tokens":
                            str(input_tokens),

                        # Prevent intermediary buffering.
                        "Cache-Control": "no-cache",
                        "X-Accel-Buffering": "no",
                    },
                )

            response = await call_model(
                request,
                BRAIN_URL,
                BRAIN_MODEL,
                messages,
                semaphore=brain_semaphore,
                model_name=BRAIN_MODEL,
                stream=False,
                **generation_parameters,
            )

        # ----------------------------------------------------
        # Return result
        # ----------------------------------------------------

        return await forward_response(
            response,
            route=route,
            input_tokens=input_tokens,
        )

    except httpx.HTTPStatusError as exc:

        logger.exception(
            "[%s] downstream HTTP error",
            request_id,
        )

        return error_response(
            (
                "Downstream llama-server returned "
                f"HTTP {exc.response.status_code}"
            ),
            502,
        )

    except Exception as exc:

        logger.exception(
            "[%s] router failure",
            request_id,
        )

        return error_response(
            str(exc),
            500,
        )


# ============================================================
# OpenAI-compatible models endpoint
# ============================================================

@app.get("/")
async def root():
    return {
        "name": "Local LLM Agent Router",
        "status": "ok",
        "api": "/v1",
        "chat_completions": "/v1/chat/completions",
        "models": "/v1/models",
        "health": "/health",
    }


@app.get("/models")
@app.get("/v1/models")
async def models():

    now = int(time.time())

    return {
        "object": "list",
        "data": [
            {
                "id": "agent-router",
                "object": "model",
                "created": now,
                "owned_by": "local-router",
            }
        ],
    }


# ============================================================
# Health endpoint
# ============================================================

@app.get("/health")
@app.get("/v1/health")
async def health():

    return {
        "status": "ok",

        "router": {
            "model": "agent-router",
        },

        "routing": {
            "token_limit": ROUTING_LIMIT,
        },

        "triager": {
            "url": TRIAGER_URL,
            "model": TRIAGER_MODEL,
            "concurrency": TRIAGER_CONCURRENCY,
            "available_slots":
                triager_semaphore._value,
        },

        "worker": {
            "url": WORKER_URL,
            "model": WORKER_MODEL,
            "concurrency": WORKER_CONCURRENCY,
            "available_slots":
                worker_semaphore._value,
        },

        "brain": {
            "url": BRAIN_URL,
            "model": BRAIN_MODEL,
            "concurrency": BRAIN_CONCURRENCY,
            "available_slots":
                brain_semaphore._value,
        },
    }


# ============================================================
# Run directly
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host=ROUTER_HOST,
        port=ROUTER_PORT,
    )
