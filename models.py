from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc)

class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=utcnow)

    # Partie / progression
    started_at: Optional[datetime] = None
    stage_started_at: Optional[datetime] = None
    current_stage: int = 0
    is_finished: bool = False
    success: bool = False

    # Chrono par étape (sec)
    stage_duration_sec: int = 120

    # Stats
    missed_count: int = 0
    score: int = 0
    wrong_attempts: int = 0

class Player(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_code: str = Field(index=True)
    code: str = Field(index=True)    # code joueur (6 hex)
    name: Optional[str] = None
    authenticated: bool = False
    joined_at: datetime = Field(default_factory=utcnow)
