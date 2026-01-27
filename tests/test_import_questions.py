"""Test question import functionality."""
import pytest
import pandas as pd
import tempfile
import os
from sqlalchemy.orm import Session
from backend.db.base import Base, engine, SessionLocal
from backend.db.models import QuestionBank
from backend.services.question_bank_loader import import_questions_from_excel


@pytest.fixture
def db_session():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_import_questions_valid(db_session: Session):
    """Test importing valid questions."""
    # Create test Excel file
    data = {
        'id': ['Q1', 'Q2', 'Q3'],
        'question': ['What is Java?', 'What is Spring?', 'What is JVM?'],
        'correct_answer': ['Java is a language', 'Spring is a framework', 'JVM is a virtual machine'],
        'difficulty': [1, 2, 3],
        'chapter': ['Java基础', 'Spring', 'JVM']
    }
    df = pd.DataFrame(data)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        df.to_excel(tmp_file.name, index=False)
        tmp_path = tmp_file.name
    
    try:
        result = import_questions_from_excel(db_session, tmp_path)
        
        assert result.total == 3
        assert result.created == 3
        assert result.updated == 0
        assert result.failed == 0
        
        # Verify questions in database
        questions = db_session.query(QuestionBank).all()
        assert len(questions) == 3
        assert questions[0].id == 'Q1'
        assert questions[0].difficulty == 1
    finally:
        os.unlink(tmp_path)


def test_import_questions_upsert(db_session: Session):
    """Test upsert functionality."""
    # Create initial question
    existing = QuestionBank(
        id='Q1',
        question='Old question',
        correct_answer='Old answer',
        difficulty=1,
        chapter='Java基础'
    )
    db_session.add(existing)
    db_session.commit()
    
    # Import with same ID but different content
    data = {
        'id': ['Q1', 'Q2'],
        'question': ['New question', 'Another question'],
        'correct_answer': ['New answer', 'Another answer'],
        'difficulty': [2, 3],
        'chapter': ['Java基础', 'Spring']
    }
    df = pd.DataFrame(data)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        df.to_excel(tmp_file.name, index=False)
        tmp_path = tmp_file.name
    
    try:
        result = import_questions_from_excel(db_session, tmp_path)
        
        assert result.total == 2
        assert result.created == 1
        assert result.updated == 1
        
        # Verify update
        updated = db_session.query(QuestionBank).filter(QuestionBank.id == 'Q1').first()
        assert updated.question == 'New question'
        assert updated.difficulty == 2
    finally:
        os.unlink(tmp_path)


def test_import_questions_invalid_header(db_session: Session):
    """Test import with invalid header."""
    data = {
        'wrong_id': ['Q1'],
        'wrong_question': ['Test'],
        'wrong_answer': ['Answer'],
        'wrong_difficulty': [1],
        'wrong_chapter': ['Test']
    }
    df = pd.DataFrame(data)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        df.to_excel(tmp_file.name, index=False)
        tmp_path = tmp_file.name
    
    try:
        result = import_questions_from_excel(db_session, tmp_path)
        
        assert result.failed == result.total
        assert result.created == 0
        assert len(result.errors) > 0
    finally:
        os.unlink(tmp_path)

