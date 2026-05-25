"""Test interview flow."""
import pytest
from sqlalchemy.orm import Session
from backend.db.base import Base, engine, SessionLocal
from backend.db.models import User, InterviewSession, QuestionBank, Resume, AskedQuestion, InterviewTurn
from backend.services.interview_engine import create_session, start_interview, submit_answer, is_resume_qa_session, end_interview
from backend.services.report_generator import generate_report
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


def test_meaningless_answer_reprompts_same_question(db_session: Session, test_user, test_questions):
    """A nonsense answer should be rejected and should not advance the interview."""
    session = create_session(
        db=db_session,
        user_id=test_user.id,
        track="Java Backend",
        level=1,
        total_rounds=5,
    )
    start_interview(db_session, session.id)
    db_session.refresh(session)
    current_round = session.current_round

    result = submit_answer(
        db=db_session,
        session_id=session.id,
        answer_text="1",
    )

    db_session.refresh(session)
    assert "error" not in result
    assert result["followup"] is True
    assert session.current_round == current_round
    assert result["evaluation"]["_answer_quality"]["category"] == "meaningless"
    assert (
        "进入下一题" in result["interviewer_message"]
        or "重新回答" in result["interviewer_message"]
        or "认真补充" in result["interviewer_message"]
    )
    turns = (
        db_session.query(InterviewTurn)
        .filter(InterviewTurn.session_id == session.id)
        .order_by(InterviewTurn.created_at, InterviewTurn.id)
        .all()
    )
    roles = [turn.role for turn in turns]
    assert "analysis" in roles
    candidate_idx = roles.index("candidate")
    analysis_idx = roles.index("analysis")
    assert analysis_idx > candidate_idx


def test_low_effort_answer_gets_followup(db_session: Session, test_user, test_questions):
    """An honest weak answer should trigger interviewer-style probing."""
    session = create_session(
        db=db_session,
        user_id=test_user.id,
        track="Java Backend",
        level=1,
        total_rounds=5,
    )
    start_interview(db_session, session.id)

    result = submit_answer(
        db=db_session,
        session_id=session.id,
        answer_text="不知道",
    )

    assert "error" not in result
    assert result["followup"] is True
    assert result["evaluation"]["_answer_quality"]["severity"] == "weak"
    assert "追问" in result["interviewer_message"] or "补充" in result["interviewer_message"]


def test_report_contains_visual_analytics_without_llm(db_session: Session, test_user, test_questions, monkeypatch):
    """Report generation should expose chart-ready analytics even without an LLM key."""
    from backend.core.config import settings

    monkeypatch.setattr(settings, "zhipuai_api_key", None)
    session = create_session(
        db=db_session,
        user_id=test_user.id,
        track="Java Backend",
        level=1,
        total_rounds=5,
    )
    start_interview(db_session, session.id)
    submit_answer(
        db=db_session,
        session_id=session.id,
        answer_text="Java is a programming language developed by Sun Microsystems and runs on the JVM.",
    )
    end_interview(db_session, session.id)

    report = generate_report(db_session, session.id)
    summary = report["summary_json"]

    assert "llm_scoring" in summary
    assert summary["llm_scoring"]["enabled"] is False
    assert "visual_analytics" in summary
    assert summary["visual_analytics"]["heatmap_rows"]
    assert summary["per_question_scores"]


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


def test_resume_qa_never_falls_back_to_question_bank(db_session: Session, test_user, test_questions):
    """Resume QA must not ask generic bank questions even when parsed fields are sparse."""
    resume = Resume(
        user_id=test_user.id,
        filename="sparse_resume.pdf",
        raw_text="Candidate built an order reconciliation service and optimized database queries.",
        parsed_json={},
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

    result = start_interview(db_session, session.id)
    assert "error" not in result

    asked_q = (
        db_session.query(AskedQuestion)
        .filter(AskedQuestion.session_id == session.id)
        .order_by(AskedQuestion.created_at.desc())
        .first()
    )
    assert asked_q is not None
    assert asked_q.qbank_id is None
    assert "What is Java?" not in asked_q.question_text
    assert "What is Spring?" not in asked_q.question_text

