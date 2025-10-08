from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Partie et progression
    started_at: Optional[datetime] = None
    current_stage: int = 0
    is_finished: bool = False
    success: bool = False

    # Chrono par étape
    stage_started_at: Optional[datetime] = None
    stage_duration_sec: int = 90            # 90s par énigme
    missed_count: int = 0                   # nb d'étapes ratées (temps écoulé)

class Player(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    room_code: str = Field(index=True)
    code: str = Field(index=True)           # code de connexion (6 hex)
    name: Optional[str] = None
    authenticated: bool = False
    joined_at: datetime = Field(default_factory=datetime.utcnow)
