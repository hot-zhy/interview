"""Interview schemas."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InterviewSessionCreate(BaseModel):
    """Interview session create schema."""
    track: str
    level: int
    resume_id: Optional[int] = None
    total_rounds: int = 10


class InterviewSessionResponse(BaseModel):
    """Interview session response schema."""
    id: int
    user_id: int
    resume_id: Optional[int]
    track: str
    level: int
    status: str
    total_rounds: int
    current_round: int
    started_at: datetime
    ended_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class InterviewTurnCreate(BaseModel):
    """Interview turn create schema."""
    session_id: int
    role: str  # interviewer or candidate
    content: str


class InterviewTurnResponse(BaseModel):
    """Interview turn response schema."""
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    """Answer submit schema."""
    session_id: int
    answer_text: str

