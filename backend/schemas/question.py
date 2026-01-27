"""Question schemas."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class QuestionBankCreate(BaseModel):
    """Question bank create schema."""
    id: str
    question: str
    correct_answer: str
    difficulty: int
    chapter: str


class QuestionBankResponse(BaseModel):
    """Question bank response schema."""
    id: str
    question: str
    correct_answer: str
    difficulty: int
    chapter: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ImportResult(BaseModel):
    """Import result schema."""
    total: int
    created: int
    updated: int
    skipped: int
    failed: int
    errors: list[str]

