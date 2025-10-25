"""
Node Agent - Executes AI inference jobs using local Ollama.

Detects available models, registers with server, receives jobs via SSE,
and streams results back in real-time.
"""

import asyncio
import json
import os
import socket
from typing import List
from contextlib import asynccontextmanager

import httpx
from httpx_sse import aconnect_sse
import ollama
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


class Job(BaseModel):
    job_id: str
    model: str
    prompt: str


with open("config.json", "r") as f:
    config = json.load(f)

NODE_ID = os.getenv("NODE_ID", socket.gethostname())
NODE_PORT = int(os.getenv("NODE_PORT", config.get("node_port", 8001)))
SERVER_URL = os.getenv("SERVER_URL", config.get("server_url"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
CONCORDIUM_ADDRESS = os.getenv("CONCORDIUM_ADDRESS", config.get("concordium_address", "test_concordium_address"))

ollama_client = ollama.Client(host=OLLAMA_HOST)


def get_available_models() -> List[str]:
    try:
        models_response = ollama_client.list()
        # Extract model names from the response
        models = [model['name'] for model in models_response.get('models', [])]
        return models
    except Exception as e:
        print(f"Error detecting Ollama models: {e}")
        return []


async def register_with_server(node_id: str, node_url: str, models: List[str], concordium_address: str = None):
    """Register this node with the server."""
    registration = {
        "node_id": node_id,
        "url": node_url,
        "models": models,
        "concordium_address": concordium_address
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SERVER_URL}/register",
                json=registration,
                timeout=10.0
            )
            response.raise_for_status()
            print(f"Successfully registered with server: {response.json()}")
    except Exception as e:
        print(f"Failed to register with server: {e}")
        raise


# ============================================================================
# FastAPI Application
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup: Register with server and start SSE listener
    models = get_available_models()

    if not models:
        print("WARNING: No Ollama models detected on this node!")
        print("Please ensure Ollama is running and has models installed.")
        print("You can install a model with: ollama pull llama3")

    # Construct node URL
    if os.getenv("DOCKER_ENV"):
        # In Docker, use the service name
        node_url = f"http://{NODE_ID}:{NODE_PORT}"
    else:
        # When running locally, use localhost so server can reach us
        node_url = f"http://localhost:{NODE_PORT}"

    print(f"Node ID: {NODE_ID}")
    print(f"Node URL: {node_url}")
    print(f"Ollama Host: {OLLAMA_HOST}")
    print(f"Concordium Address: {CONCORDIUM_ADDRESS}")
    print(f"Available models: {models}")

    await register_with_server(NODE_ID, node_url, models, CONCORDIUM_ADDRESS)

    # Start SSE listener (replaces polling for instant job delivery)
    sse_task = asyncio.create_task(listen_for_jobs_sse())
    print("Started SSE listener for instant job delivery")

    yield

    # Shutdown: Cancel SSE listener
    sse_task.cancel()


app = FastAPI(title="Ollama Node Agent", lifespan=lifespan)


# ============================================================================
# Job Execution
# ============================================================================

async def execute_job(job: Job):
    """
    Execute an AI inference job and stream results to the server.

    Steps:
    1. Check if we have the requested model
    2. Send metadata (which node is handling this)
    3. Run the AI model
    4. Stream each token (word/part of word) as it's generated
    5. Tell server we're done
    """
    try:
        # Step 1: Make sure we have the model they're asking for
        available_models = get_available_models()

        if job.model not in available_models:
            error = f"Model {job.model} not available on this node"
            print(f"Error executing job {job.job_id}: {error}")
            # Tell server we can't do this job
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{SERVER_URL}/jobs/{job.job_id}/done",
                    params={"error": error}
                )
            return

        print(f"Executing job {job.job_id} with model {job.model}")

        # Step 2: Tell the client which node is handling their request
        metadata = json.dumps({
            "node_id": NODE_ID,
            "node_url": f"http://localhost:{NODE_PORT}",
            "metadata": True
        }) + "\n"

        async with httpx.AsyncClient(timeout=300.0) as client:
            # Send metadata chunk first
            await client.post(
                f"{SERVER_URL}/jobs/{job.job_id}/chunk",
                json={"chunk": metadata}
            )

            # Step 3: Run the AI model and get a stream of responses
            # stream=True means we get results word-by-word, not all at once
            stream = ollama_client.chat(
                model=job.model,
                messages=[{'role': 'user', 'content': job.prompt}],
                stream=True,
            )

            # Track token counts (will be in the final chunk)
            token_counts = {}

            # Step 4: Send each token (word/piece) as it comes out
            for chunk in stream:
                # Check if this is the final chunk with metadata
                if chunk.get('done', False):
                    # Extract token counts from the final chunk
                    token_counts = {
                        "prompt_tokens": chunk.get('prompt_eval_count', 0),
                        "completion_tokens": chunk.get('eval_count', 0),
                        "total_tokens": chunk.get('prompt_eval_count', 0) + chunk.get('eval_count', 0)
                    }
                    break

                # Ollama returns chunks with different structures,
                # we only want the actual text content
                if 'message' in chunk and 'content' in chunk['message']:
                    token = chunk['message']['content']
                    response = json.dumps({
                        "token": token,
                        "done": False
                    }) + "\n"

                    # Send this token to the server immediately
                    await client.post(
                        f"{SERVER_URL}/jobs/{job.job_id}/chunk",
                        json={"chunk": response}
                    )

            # Step 5: Send the "we're done" signal with token counts
            final_response = json.dumps({
                "done": True,
                "token_counts": token_counts
            }) + "\n"
            await client.post(
                f"{SERVER_URL}/jobs/{job.job_id}/chunk",
                json={"chunk": final_response}
            )

            # Mark the job as complete
            await client.post(f"{SERVER_URL}/jobs/{job.job_id}/done")

        # Log completion with token counts
        if token_counts:
            print(f"Job {job.job_id} completed successfully - "
                  f"{token_counts.get('total_tokens', 0)} tokens "
                  f"(prompt: {token_counts.get('prompt_tokens', 0)}, "
                  f"completion: {token_counts.get('completion_tokens', 0)})")
        else:
            print(f"Job {job.job_id} completed successfully")

    except Exception as e:
        print(f"Error executing job {job.job_id}: {e}")
        error_response = json.dumps({
            "error": str(e),
            "done": True
        }) + "\n"

        async with httpx.AsyncClient() as client:
            await client.post(
                f"{SERVER_URL}/jobs/{job.job_id}/chunk",
                json={"chunk": error_response}
            )
            await client.post(
                f"{SERVER_URL}/jobs/{job.job_id}/done",
                params={"error": str(e)}
            )


# ============================================================================
# SSE Job Listener (with automatic reconnection)
# ============================================================================

async def listen_for_jobs_sse():
    """
    Maintain a persistent SSE connection to receive jobs instantly.

    HOW IT WORKS:
    1. Connect to server's /stream endpoint
    2. Wait for events (jobs, heartbeats, etc.)
    3. When a job arrives, execute it immediately
    4. If connection drops, automatically reconnect with backoff

    This replaces polling - instead of asking "any jobs?" every 2 seconds,
    the server pushes jobs to us as soon as they arrive.
    """
    retry_delay = 1  # Start with 1 second delay
    max_retry_delay = 60  # Don't wait more than 60 seconds between retries

    while True:
        try:
            # Get our available models
            models = get_available_models()
            if not models:
                print("No models available, waiting 5 seconds before retry")
                await asyncio.sleep(5)
                continue

            models_str = ",".join(models)

            print(f"Connecting to SSE stream at {SERVER_URL}/stream")

            # Open persistent SSE connection
            async with httpx.AsyncClient(timeout=None) as client:
                async with aconnect_sse(
                    client,
                    "GET",
                    f"{SERVER_URL}/stream",
                    params={"node_id": NODE_ID, "models": models_str}
                ) as event_source:

                    print(f"SSE connection established for node {NODE_ID}")
                    retry_delay = 1  # Reset retry delay on successful connection

                    # Listen for events from the server
                    async for event in event_source.aiter_sse():
                        # Event types:
                        # - "connected": Connection confirmed
                        # - "heartbeat": Keep-alive ping
                        # - "job": New job to execute

                        if event.event == "connected":
                            data = json.loads(event.data)
                            print(f"Connected to server: {data}")

                        elif event.event == "heartbeat":
                            # Just a keep-alive, no action needed
                            # (prevents timeout on quiet connections)
                            pass

                        elif event.event == "job":
                            # Parse job data and execute it
                            job_data = json.loads(event.data)
                            job = Job(**job_data)
                            print(f"Received job via SSE: {job.job_id}")

                            # Execute job in background (don't block SSE listener)
                            asyncio.create_task(execute_job(job))

                        else:
                            print(f"Unknown SSE event type: {event.event}")

        except Exception as e:
            # Connection lost or error occurred
            print(f"SSE connection error: {e}")
            print(f"Reconnecting in {retry_delay} seconds...")

            # Wait before reconnecting
            await asyncio.sleep(retry_delay)

            # Exponential backoff: double the delay each time, up to max
            retry_delay = min(retry_delay * 2, max_retry_delay)


# ============================================================================
# Legacy Polling (Fallback)
# ============================================================================

async def poll_for_jobs():
    """
    Legacy polling fallback if SSE is unavailable.

    This is kept for backward compatibility but not used by default.
    SSE (listen_for_jobs_sse) provides instant job delivery.
    """
    poll_interval = config.get("poll_interval", 2)

    while True:
        try:
            models = get_available_models()
            if not models:
                print("No models available, skipping poll")
                await asyncio.sleep(poll_interval)
                continue

            models_str = ",".join(models)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{SERVER_URL}/poll",
                    params={"node_id": NODE_ID, "models": models_str},
                    timeout=10.0
                )

                if response.status_code == 200:
                    job_data = response.json()
                    job = Job(**job_data)
                    print(f"Received job via polling: {job.job_id}")
                    asyncio.create_task(execute_job(job))

        except httpx.HTTPStatusError as e:
            if e.response.status_code != 204:
                print(f"Polling error: {e}")
        except Exception as e:
            print(f"Polling error: {e}")

        await asyncio.sleep(poll_interval)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "node_id": NODE_ID,
        "models": get_available_models()
    }


@app.get("/models")
async def list_models():
    """List available models on this node."""
    return {
        "node_id": NODE_ID,
        "models": get_available_models()
    }


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=NODE_PORT)
