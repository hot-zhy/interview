"""Database models."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.db.base import Base


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    interviews = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    """Resume model."""
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    raw_text = Column(Text)
    parsed_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="resumes")
    interviews = relationship("InterviewSession", back_populates="resume")


class QuestionBank(Base):
    """Question bank model."""
    __tablename__ = "question_bank"
    
    id = Column(String(100), primary_key=True, index=True)  # String to support both int and str IDs
    question = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    difficulty = Column(Integer, nullable=False)
    chapter = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    asked_questions = relationship("AskedQuestion", back_populates="question_bank")


class InterviewSession(Base):
    """Interview session model."""
    __tablename__ = "interview_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    track = Column(String(100), nullable=False)
    level = Column(Integer, nullable=False)  # Initial difficulty level
    status = Column(String(50), default="active")  # active, completed, cancelled
    total_rounds = Column(Integer, default=10)
    current_round = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    expression_history_json = Column(JSON, nullable=True)  # Real-time expression samples from video stream
    
    # Relationships
    user = relationship("User", back_populates="interviews")
    resume = relationship("Resume", back_populates="interviews")
    turns = relationship("InterviewTurn", back_populates="session", cascade="all, delete-orphan")
    asked_questions = relationship("AskedQuestion", back_populates="session", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="session", uselist=False, cascade="all, delete-orphan")


class InterviewTurn(Base):
    """Interview turn (conversation) model."""
    __tablename__ = "interview_turns"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    role = Column(String(50), nullable=False)  # interviewer or candidate
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("InterviewSession", back_populates="turns")


class AskedQuestion(Base):
    """Asked question in interview."""
    __tablename__ = "asked_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    qbank_id = Column(String(100), ForeignKey("question_bank.id"), nullable=True)
    topic = Column(String(100), nullable=False)  # chapter
    difficulty = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    correct_answer_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("InterviewSession", back_populates="asked_questions")
    question_bank = relationship("QuestionBank", back_populates="asked_questions")
    evaluation = relationship("Evaluation", back_populates="asked_question", uselist=False, cascade="all, delete-orphan")


class Evaluation(Base):
    """Evaluation model."""
    __tablename__ = "evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    asked_question_id = Column(Integer, ForeignKey("asked_questions.id"), nullable=False, unique=True)
    answer_text = Column(Text, nullable=False)
    scores_json = Column(JSON, nullable=False)  # {correctness, depth, clarity, practicality, tradeoffs}
    overall_score = Column(Float, nullable=False)
    feedback_text = Column(Text, nullable=False)
    missing_points_json = Column(JSON)  # List of missing points
    next_direction = Column(Text)  # Next question direction
    speech_analysis_json = Column(JSON, nullable=True)  # Speech analysis results
    expression_analysis_json = Column(JSON, nullable=True)  # Facial expression analysis results
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    asked_question = relationship("AskedQuestion", back_populates="evaluation")


class Report(Base):
    """Interview report model."""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False, unique=True)
    summary_json = Column(JSON, nullable=False)
    markdown = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("InterviewSession", back_populates="report")

