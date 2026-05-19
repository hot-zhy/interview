"""Test interview flow."""
import pytest
from sqlalchemy.orm import Session
from backend.db.base import Base, engine, SessionLocal
from backend.db.models import User, InterviewSession, QuestionBank, Resume, AskedQuestion
from backend.services.interview_engine import create_session, start_interview, submit_answer, is_resume_qa_session
from backend.core.security import get_password_hash


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


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("password123")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_questions(db_session: Session):
    """Create test questions."""
    questions = [
        QuestionBank(
            id='Q1',
            question='What is Java?',
            correct_answer='Java is a programming language',
            difficulty=1,
            chapter='Java基础'
        ),
        QuestionBank(
            id='Q2',
            question='What is Spring?',
            correct_answer='Spring is a framework',
            difficulty=2,
            chapter='Spring'
        ),
    ]
    for q in questions:
        db_session.add(q)
    db_session.commit()
    return questions


def test_create_session(db_session: Session, test_user):
    """Test creating an interview session."""
    session = create_session(
        db=db_session,
        user_id=test_user.id,
        track="Java Backend",
        level=2,
        total_rounds=5
    )
    
    assert session.id is not None
    assert session.user_id == test_user.id
    assert session.track == "Java Backend"
    assert session.level == 2
    assert session.status == "active"
    assert session.current_round == 0


def test_start_interview(db_session: Session, test_user, test_questions):
    """Test starting an interview."""
    session = create_session(
        db=db_session,
        user_id=test_user.id,
        track="Java Backend",
        level=1,
        total_rounds=5
    )
    
    result = start_interview(db_session, session.id)
    
    assert "error" not in result
    assert "question" in result
    assert result["round"] == 1
    
    # Verify session updated
    db_session.refresh(session)
    assert session.current_round == 1


def test_submit_answer(db_session: Session, test_user, test_questions):
    """Test submitting an answer."""
    session = create_session(
        db=db_session,
        user_id=test_user.id,
        track="Java Backend",
        level=1,
        total_rounds=5
    )
    
    # Start interview
    start_interview(db_session, session.id)
    
    # Submit answer
    result = submit_answer(
        db=db_session,
        session_id=session.id,
        answer_text="Java is a programming language developed by Sun Microsystems"
    )
    
    assert "error" not in result
    assert "evaluation" in result
    assert "overall_score" in result["evaluation"]
    
    # Verify session updated
    db_session.refresh(session)
    assert session.current_round > 1


def test_resume_qa_uses_only_resume_probes_until_complete(db_session: Session, test_user, test_questions):
    """Resume-only interview should keep asking resume probes and never enter the question bank."""
    resume = Resume(
        user_id=test_user.id,
        filename="resume.pdf",
        parsed_json={
            "skills": ["Java", "Spring Boot", "MySQL"],
            "projects": ["Order service with Spring Boot and MySQL"],
            "experience": [],
            "education": [],
        },
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    session = create_session(
        db=db_session,
        user_id=test_user.id,
        track="Java Backend",
        level=3,
        resume_id=resume.id,
        total_rounds=3,
        interview_mode="resume_qa",
    )

    assert is_resume_qa_session(session)

    start_result = start_interview(db_session, session.id)
    assert "error" not in start_result

    asked_q = (
        db_session.query(AskedQuestion)
        .filter(AskedQuestion.session_id == session.id)
        .order_by(AskedQuestion.created_at.desc())
        .first()
    )
    assert asked_q is not None
    assert asked_q.qbank_id is None

    result = {}
    for _ in range(4):
        asked_q = (
            db_session.query(AskedQuestion)
            .filter(AskedQuestion.session_id == session.id)
            .order_by(AskedQuestion.created_at.desc())
            .first()
        )
        assert asked_q is not None
        assert asked_q.qbank_id is None

        result = submit_answer(
            db=db_session,
            session_id=session.id,
            answer_text=(
                f"{asked_q.correct_answer_text} In this project I owned the implementation, "
                "made the technical tradeoffs, verified the result with metrics, and handled rollout risks."
            ),
        )
        db_session.refresh(session)
        if session.status == "completed":
            break

    db_session.refresh(session)
    assert "evaluation" in result
    assert session.status == "completed"
    assert (
        db_session.query(AskedQuestion)
        .filter(AskedQuestion.session_id == session.id, AskedQuestion.qbank_id.isnot(None))
        .count()
        == 0
    )

