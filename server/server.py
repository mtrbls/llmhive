"""
Distributed Ollama Inference Server

Coordinates AI inference requests between clients and compute nodes.
Nodes register with available models, server assigns jobs via SSE or polling.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from enum import Enum

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import gradio as gr

# Database imports
from models import Job as DBJob, Payment, init_db, get_session

# UI imports
from ui import create_ui


STREAM_CHECK_INTERVAL = 0.1
MAX_JOB_TIMEOUT = 300
CHECKS_PER_SECOND = int(1 / STREAM_CHECK_INTERVAL)


# ============================================================================
# Data Models
# ============================================================================

class NodeRegistration(BaseModel):
    node_id: str
    url: str
    models: List[str]
    concordium_address: Optional[str] = None  # Concordium wallet for payments


class NodeInfo(BaseModel):
    node_id: str
    url: str
    models: List[str]
    concordium_address: Optional[str] = None
    last_seen: datetime


class InferenceRequest(BaseModel):
    model: str
    prompt: str


class Job(BaseModel):
    job_id: str
    model: str
    prompt: str


class JobStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class JobChunk(BaseModel):
    chunk: str


class PaymentConfirmation(BaseModel):
    job_id: str
    transaction_hash: str
    amount: float


class JobQueue:
    """Manages inference job queue and results."""

    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.pending: Dict[str, List[str]] = {}

    def add_job(self, job: Job) -> None:
        self.jobs[job.job_id] = {
            "status": JobStatus.PENDING,
            "model": job.model,
            "prompt": job.prompt,
            "chunks": [],
            "done": False,
            "error": None,
            "created_at": datetime.now()
        }

        if job.model not in self.pending:
            self.pending[job.model] = []
        self.pending[job.model].append(job.job_id)
        print(f"Job {job.job_id} queued for model {job.model}")

    def get_next_job(self, models: List[str]) -> Optional[Job]:
        for model in models:
            if model in self.pending and self.pending[model]:
                job_id = self.pending[model].pop(0)
                job_data = self.jobs[job_id]
                job_data["status"] = JobStatus.IN_PROGRESS
                print(f"Job {job_id} assigned to node with model {model}")
                return Job(
                    job_id=job_id,
                    model=job_data["model"],
                    prompt=job_data["prompt"]
                )
        return None

    def add_chunk(self, job_id: str, chunk: str) -> None:
        if job_id in self.jobs:
            self.jobs[job_id]["chunks"].append(chunk)

    def mark_done(self, job_id: str, error: Optional[str] = None) -> None:
        if job_id in self.jobs:
            if error:
                self.jobs[job_id]["status"] = JobStatus.FAILED
                self.jobs[job_id]["error"] = error
            else:
                self.jobs[job_id]["status"] = JobStatus.COMPLETED
            self.jobs[job_id]["done"] = True
            print(f"Job {job_id} marked as {self.jobs[job_id]['status']}")

    def get_chunks(self, job_id: str) -> List[str]:
        if job_id in self.jobs:
            return self.jobs[job_id]["chunks"]
        return []

    def is_done(self, job_id: str) -> bool:
        if job_id in self.jobs:
            return self.jobs[job_id]["done"]
        return False

    def get_status(self, job_id: str) -> Optional[JobStatus]:
        if job_id in self.jobs:
            return self.jobs[job_id]["status"]
        return None


class Registry:
    """Tracks which nodes have which models. Uses round-robin for load balancing."""

    def __init__(self):
        self.model_to_nodes: Dict[str, List[NodeInfo]] = {}
        self.nodes: Dict[str, NodeInfo] = {}
        self.round_robin_index: Dict[str, int] = {}

    def register_node(self, registration: NodeRegistration) -> None:
        node_info = NodeInfo(
            node_id=registration.node_id,
            url=registration.url,
            models=registration.models,
            concordium_address=registration.concordium_address,
            last_seen=datetime.now()
        )

        self.nodes[registration.node_id] = node_info

        for model in registration.models:
            if model not in self.model_to_nodes:
                self.model_to_nodes[model] = []

            self.model_to_nodes[model] = [
                n for n in self.model_to_nodes[model]
                if n.node_id != registration.node_id
            ]

            self.model_to_nodes[model].append(node_info)

    def get_node_for_model(self, model: str) -> Optional[NodeInfo]:
        if model not in self.model_to_nodes or not self.model_to_nodes[model]:
            return None

        if model not in self.round_robin_index:
            self.round_robin_index[model] = 0

        nodes = self.model_to_nodes[model]
        index = self.round_robin_index[model] % len(nodes)
        self.round_robin_index[model] = (index + 1) % len(nodes)

        return nodes[index]

    def get_all_nodes(self) -> List[NodeInfo]:
        return list(self.nodes.values())

    def update_node_heartbeat(self, node_id: str) -> None:
        if node_id in self.nodes:
            self.nodes[node_id].last_seen = datetime.now()

    def prune_stale_nodes(self, timeout_seconds: int) -> None:
        cutoff_time = datetime.now() - timedelta(seconds=timeout_seconds)
        stale_node_ids = [
            node_id for node_id, node in self.nodes.items()
            if node.last_seen < cutoff_time
        ]

        for node_id in stale_node_ids:
            node = self.nodes.pop(node_id)
            # Remove from model registry
            for model in node.models:
                if model in self.model_to_nodes:
                    self.model_to_nodes[model] = [
                        n for n in self.model_to_nodes[model]
                        if n.node_id != node_id
                    ]
            print(f"Pruned stale node: {node_id}")


async def health_check_task(registry: Registry, config: dict):
    interval = config.get("health_check_interval", 30)
    timeout = config.get("health_check_timeout", 5)

    async with httpx.AsyncClient(timeout=timeout) as client:
        while True:
            await asyncio.sleep(interval)

            for node in registry.get_all_nodes():
                # If node has active SSE connection, it's alive
                if node.node_id in sse_connections:
                    registry.update_node_heartbeat(node.node_id)
                    continue

                # Fallback: try HTTP health check for nodes without SSE
                try:
                    response = await client.get(f"{node.url}/health")
                    if response.status_code == 200:
                        registry.update_node_heartbeat(node.node_id)
                except Exception as e:
                    # Only log if node doesn't have SSE connection
                    # (SSE nodes behind NAT/firewall will fail HTTP checks)
                    pass

            # Prune nodes that haven't responded in 2x the interval
            registry.prune_stale_nodes(interval * 2)


with open("config.json", "r") as f:
    config = json.load(f)

registry = Registry()
job_queue = JobQueue()
sse_connections: Dict[str, asyncio.Queue] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database initialized")

    task = asyncio.create_task(health_check_task(registry, config))
    yield
    task.cancel()


app = FastAPI(title="Ollama Server", lifespan=lifespan)

# Add CORS middleware to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/register")
async def register_node(registration: NodeRegistration):
    registry.register_node(registration)
    return {
        "status": "registered",
        "node_id": registration.node_id,
        "models": registration.models
    }


@app.get("/stream")
async def stream_jobs(request: Request, node_id: str, models: str):
    """SSE endpoint for instant job delivery to nodes."""
    registry.update_node_heartbeat(node_id)

    model_list = [m.strip() for m in models.split(",") if m.strip()]

    queue = asyncio.Queue()
    sse_connections[node_id] = queue

    print(f"Node {node_id} connected via SSE with models: {model_list}")

    async def event_generator():
        try:
            yield {
                "event": "connected",
                "data": json.dumps({"status": "connected", "node_id": node_id})
            }

            while True:
                if await request.is_disconnected():
                    print(f"Node {node_id} disconnected (client closed connection)")
                    break

                try:
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)

                    # Handle both Job objects and payment notification dicts
                    if isinstance(item, dict) and item.get("type") == "payment_received":
                        yield {
                            "event": "payment_received",
                            "data": json.dumps(item)
                        }
                    else:
                        # Regular job
                        yield {
                            "event": "job",
                            "data": json.dumps(item.model_dump())
                        }

                except asyncio.TimeoutError:
                    # Update heartbeat timestamp to keep node alive
                    registry.update_node_heartbeat(node_id)
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": datetime.now().isoformat()})
                    }

        finally:
            if node_id in sse_connections:
                del sse_connections[node_id]
            print(f"Node {node_id} SSE connection closed")

    return EventSourceResponse(event_generator())


@app.get("/poll")
async def poll_for_job(node_id: str, models: str):
    """Legacy polling endpoint. Returns 204 if no jobs available."""
    registry.update_node_heartbeat(node_id)

    model_list = [m.strip() for m in models.split(",") if m.strip()]
    job = job_queue.get_next_job(model_list)

    if job:
        return job
    else:
        raise HTTPException(status_code=204, detail="No jobs available")


@app.get("/nodes")
async def list_nodes():
    nodes = registry.get_all_nodes()

    return {
        "nodes": [
            {
                "node_id": node.node_id,
                "url": node.url,
                "models": node.models,
                "last_seen": node.last_seen.isoformat()
            }
            for node in nodes
        ]
    }


@app.get("/models")
async def list_models():
    """Get all available models from registered nodes"""
    models = set()
    for node in registry.get_all_nodes():
        models.update(node.models)
    return {
        "models": sorted(list(models))
    }


@app.post("/jobs/{job_id}/chunk")
async def receive_chunk(job_id: str, chunk: JobChunk):
    job_queue.add_chunk(job_id, chunk.chunk)
    return {"status": "received"}


@app.post("/jobs/{job_id}/done")
async def mark_job_done(job_id: str, error: Optional[str] = None):
    job_queue.mark_done(job_id, error)

    with get_session() as session:
        db_job = session.get(DBJob, job_id)
        if db_job:
            db_job.status = "failed" if error else "completed"
            db_job.completed_at = datetime.utcnow()

            chunks = job_queue.get_chunks(job_id)
            for chunk in chunks:
                try:
                    data = json.loads(chunk.strip())
                    if "token_counts" in data:
                        db_job.prompt_tokens = data["token_counts"].get("prompt_tokens")
                        db_job.completion_tokens = data["token_counts"].get("completion_tokens")
                        db_job.total_tokens = data["token_counts"].get("total_tokens")
                    if data.get("metadata") and "node_id" in data:
                        db_job.node_id = data["node_id"]
                        if db_job.node_id in registry.nodes:
                            node_info = registry.nodes[db_job.node_id]
                            db_job.node_address = node_info.concordium_address
                except:
                    pass

            session.commit()
            print(f"Updated database record for job {job_id}: {db_job.status}")

    return {"status": "done"}


@app.post("/inference")
async def inference(request: InferenceRequest):
    """Queue inference request and stream response as it arrives."""
    node = registry.get_node_for_model(request.model)
    if not node:
        raise HTTPException(
            status_code=404,
            detail=f"No node available with model: {request.model}"
        )

    job_id = f"job-{datetime.now().timestamp()}"
    job = Job(job_id=job_id, model=request.model, prompt=request.prompt)

    with get_session() as session:
        db_job = DBJob(
            job_id=job_id,
            model=request.model,
            status="pending"
        )
        session.add(db_job)
        session.commit()
        print(f"Created database record for job {job_id}")

    job_queue.add_job(job)

    pushed_to_sse = False
    for node_id, queue in sse_connections.items():
        if node_id in registry.nodes:
            node_info = registry.nodes[node_id]
            if request.model in node_info.models:
                await queue.put(job)
                job_queue.jobs[job_id]["status"] = JobStatus.IN_PROGRESS
                pushed_to_sse = True
                print(f"Job {job_id} pushed to node {node_id} via SSE (instant)")
                break

    if not pushed_to_sse:
        print(f"Job {job_id} waiting for polling (no SSE connection available)")

    async def stream_chunks():
        last_chunk_index = 0
        timeout_count = 0

        while not job_queue.is_done(job_id):
            all_chunks = job_queue.get_chunks(job_id)

            for i in range(last_chunk_index, len(all_chunks)):
                yield all_chunks[i]
                last_chunk_index = i + 1

            await asyncio.sleep(STREAM_CHECK_INTERVAL)

            timeout_count += 1
            if timeout_count > MAX_JOB_TIMEOUT * CHECKS_PER_SECOND:
                error_msg = json.dumps({
                    "error": "Job timeout",
                    "done": True
                }) + "\n"
                yield error_msg
                break

        all_chunks = job_queue.get_chunks(job_id)
        for i in range(last_chunk_index, len(all_chunks)):
            yield all_chunks[i]

    return StreamingResponse(
        stream_chunks(),
        media_type="application/x-ndjson",
        headers={"X-Job-ID": job_id}
    )


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    with get_session() as session:
        db_job = session.get(DBJob, job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Calculate payment amount if job is completed
        payment_info = None
        if db_job.total_tokens and db_job.node_address:
            price_per_token = config.get("pricing", {}).get("price_per_token", 0.0001)
            amount_ccd = db_job.total_tokens * price_per_token

            payment_info = {
                "amount_ccd": amount_ccd,
                "recipient_address": db_job.node_address,
                "recipient_node": db_job.node_id
            }

        return {
            "job_id": db_job.job_id,
            "status": db_job.status,
            "model": db_job.model,
            "node_id": db_job.node_id,
            "node_address": db_job.node_address,
            "token_counts": {
                "prompt_tokens": db_job.prompt_tokens,
                "completion_tokens": db_job.completion_tokens,
                "total_tokens": db_job.total_tokens
            } if db_job.total_tokens else None,
            "payment": payment_info,
            "created_at": db_job.created_at.isoformat() if db_job.created_at else None,
            "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None
        }


@app.post("/payment-confirmed")
async def payment_confirmed(confirmation: PaymentConfirmation):
    """
    Receive payment confirmation from client and notify node via SSE.
    """
    # Update payment record in database
    with get_session() as session:
        db_job = session.query(DBJob).filter_by(job_id=confirmation.job_id).first()
        if not db_job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Update or create payment record
        payment = session.query(Payment).filter_by(job_id=confirmation.job_id).first()
        if payment:
            payment.transaction_hash = confirmation.transaction_hash
            payment.paid = True
        else:
            payment = Payment(
                job_id=confirmation.job_id,
                amount_ccd=confirmation.amount,
                recipient_address=db_job.node_address,
                transaction_hash=confirmation.transaction_hash,
                paid=True
            )
            session.add(payment)

        session.commit()
        node_id = db_job.node_id
        print(f"Payment confirmed for job {confirmation.job_id}: {confirmation.transaction_hash}")

    # Send payment notification to node via SSE
    if node_id and node_id in sse_connections:
        payment_event = {
            "type": "payment_received",
            "job_id": confirmation.job_id,
            "amount": confirmation.amount,
            "transaction_hash": confirmation.transaction_hash
        }
        await sse_connections[node_id].put(payment_event)
        print(f"Sent payment notification to node {node_id} via SSE")

    return {"status": "payment_confirmed", "job_id": confirmation.job_id}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# Mount static files for wallet.js
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount Gradio UI at root path
# Use operator_url from config (defaults to localhost:8000 for coordinator/operator service)
operator_url = config.get('operator_url', 'http://localhost:8000')
gradio_app = create_ui(operator_url=operator_url)
app = gr.mount_gradio_app(app, gradio_app, path="/")

print(f"Gradio UI mounted at {operator_url}/")


if __name__ == "__main__":
    import uvicorn
    port = config.get("server_port", 8000)
    uvicorn.run(app, host="0.0.0.0", port=port)
