"""Resume schemas."""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ResumeCreate(BaseModel):
    """Resume create schema."""
    filename: str
    raw_text: Optional[str] = None
    parsed_json: Optional[Dict[str, Any]] = None


class ResumeUpdate(BaseModel):
    """Resume update schema."""
    parsed_json: Optional[Dict[str, Any]] = None


class ResumeResponse(BaseModel):
    """Resume response schema."""
    id: int
    user_id: int
    filename: str
    raw_text: Optional[str]
    parsed_json: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

