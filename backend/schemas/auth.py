"""Authentication schemas."""
from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    """User registration schema."""
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response schema."""
    id: int
    email: str
    
    class Config:
        from_attributes = True

