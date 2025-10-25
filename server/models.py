"""
Database models for ODLA distributed inference system.

Uses SQLModel (Pydantic + SQLAlchemy) for type-safe database operations.
"""

import json
import os
from pathlib import Path
from sqlmodel import SQLModel, Field, create_engine, Session
from datetime import datetime
from typing import Optional


class Job(SQLModel, table=True):
    """
    Job record tracking inference requests from creation to completion.

    Lifecycle:
    1. Created with status='pending' when client submits inference
    2. Updated to status='running' when assigned to node
    3. Updated to status='completed' with token counts when node finishes
    4. status='failed' if something goes wrong
    """
    job_id: str = Field(primary_key=True)
    status: str = Field(default="pending")  # pending | running | completed | failed
    model: str
    node_id: Optional[str] = None
    node_address: Optional[str] = None  # Concordium wallet address for payments
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class Payment(SQLModel, table=True):
    """
    Payment record linking jobs to blockchain transactions.

    Optional: Clients can submit payment tx hash for tracking,
    but blockchain is source of truth (can verify independently).
    """
    job_id: str = Field(primary_key=True, foreign_key="job.job_id")
    amount_ccd: float
    payment_tx: Optional[str] = None  # Concordium transaction hash
    paid_at: Optional[datetime] = None


# Database engine and session
# SQLite for simplicity - can upgrade to Postgres later if needed

# Load database URL from config
with open("config.json", "r") as f:
    config = json.load(f)
    DATABASE_URL = config.get("database", {}).get("url", "sqlite:///data/odla.db")

# Ensure data directory exists for SQLite databases
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:  # Only create if there's a directory component
        Path(db_dir).mkdir(parents=True, exist_ok=True)
        print(f"Ensured database directory exists: {db_dir}")

engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """Create database tables. Call on application startup."""
    SQLModel.metadata.create_all(engine)
    print(f"Database initialized at: {DATABASE_URL}")


def get_session():
    """Get database session for queries/updates."""
    return Session(engine)
