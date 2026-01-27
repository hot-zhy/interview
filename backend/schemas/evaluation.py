"""Evaluation schemas."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class Scores(BaseModel):
    """Evaluation scores."""
    correctness: float
    depth: float
    clarity: float
    practicality: float
    tradeoffs: float


class EvaluationCreate(BaseModel):
    """Evaluation create schema."""
    asked_question_id: int
    answer_text: str
    scores_json: Dict[str, float]
    overall_score: float
    feedback_text: str
    missing_points_json: Optional[List[str]] = None
    next_direction: Optional[str] = None


class EvaluationResponse(BaseModel):
    """Evaluation response schema."""
    id: int
    asked_question_id: int
    answer_text: str
    scores_json: Dict[str, float]
    overall_score: float
    feedback_text: str
    missing_points_json: Optional[List[str]]
    next_direction: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

