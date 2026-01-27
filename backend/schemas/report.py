"""Report schemas."""
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime


class ReportSummary(BaseModel):
    """Report summary schema."""
    overall_score: float
    strengths: List[str]
    weaknesses: List[str]
    missing_knowledge: List[str]
    learning_plan: List[str]
    recommended_questions: List[str]  # Question IDs


class ReportResponse(BaseModel):
    """Report response schema."""
    id: int
    session_id: int
    summary_json: Dict[str, Any]
    markdown: str
    created_at: datetime
    
    class Config:
        from_attributes = True

