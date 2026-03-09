"""Interview engine - state machine for interview flow."""
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from backend.db.models import (
    InterviewSession, InterviewTurn, AskedQuestion, Evaluation,
    QuestionBank, Resume
)
from backend.services.question_selector import select_question, adjust_difficulty
from backend.services.evaluator_rules import evaluate_answer
from backend.services.llm_provider import evaluate_with_llm, generate_followup_with_llm
from backend.services.adaptive_interview import AdaptiveInterviewEngine
from backend.services.audio_processor import process_audio_answer
from backend.services.expression_analyzer import analyze_expression
from backend.services.interview_phrases import (
    get_first_question_phrase,
    get_next_question_phrase,
    get_followup_phrase,
)


def create_session(
    db: Session,
    user_id: int,
    track: str,
    level: int,
    resume_id: Optional[int] = None,
    total_rounds: int = 10
) -> InterviewSession:
    """Create a new interview session."""
    session = InterviewSession(
        user_id=user_id,
        resume_id=resume_id,
        track=track,
        level=level,
        total_rounds=total_rounds,
        current_round=0,
        status="active"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def start_interview(db: Session, session_id: int) -> Optional[Dict]:
    """Start interview - get first question."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session or session.status != "active":
        return None
    
    # Get resume skills if available
    resume_skills = None
    if session.resume_id:
        resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
        if resume and resume.parsed_json:
            resume_skills = resume.parsed_json.get("skills", [])
    
    # Select first question
    question = select_question(
        db=db,
        session=session,
        current_difficulty=session.level,
        resume_skills=resume_skills
    )
    
    if not question:
        return {
            "error": "题库中没有可用题目，请先导入题库。"
        }
    
    # Create asked question record
    asked_q = AskedQuestion(
        session_id=session_id,
        qbank_id=question.id,
        topic=question.chapter,
        difficulty=question.difficulty,
        question_text=question.question,
        correct_answer_text=question.correct_answer
    )
    db.add(asked_q)
    
    # Create interviewer turn (自适应开场语，有简历时体现个性化)
    has_resume = bool(session.resume_id)
    intro_content = get_first_question_phrase(question.question, has_resume=has_resume)
    interviewer_turn = InterviewTurn(
        session_id=session_id,
        role="interviewer",
        content=intro_content
    )
    db.add(interviewer_turn)
    
    session.current_round = 1
    db.commit()
    
    return {
        "question": question.question,
        "turn_id": interviewer_turn.id,
        "round": session.current_round
    }


def submit_answer(
    db: Session,
    session_id: int,
    answer_text: Optional[str] = None,
    answer_type: str = "text",
    audio_data: Optional[Dict] = None,
    expression_data: Optional[Dict] = None
) -> Dict:
    """Submit answer and get evaluation + next question.
    
    Args:
        db: Database session
        session_id: Interview session ID
        answer_text: Text answer (for text mode, required)
        answer_type: "text" or "audio"
        audio_data: Audio data dict with base64 audio and metadata (for audio mode)
        expression_data: Optional. Supports:
            - {"imageData": base64_str}: legacy single-photo mode
            - {"analyses": [...]}: real-time video mode, pre-computed analyses from video stream
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session or session.status != "active":
        return {"error": "面试会话不存在或已结束"}
    
    # Process answer based on type
    audio_analysis = None
    expression_analysis = None

    # Optional: facial expression - real-time analyses or legacy single image
    if expression_data:
        if expression_data.get("analyses"):
            # Real-time video mode: use most recent for this evaluation, append all to session history
            analyses = expression_data["analyses"]
            if analyses:
                # Remove internal _timestamp for storage
                latest = {k: v for k, v in analyses[-1].items() if not k.startswith("_")}
                expression_analysis = latest
            # Append to session-level expression history
            existing_history = session.expression_history_json or []
            for a in analyses:
                clean = {k: v for k, v in a.items() if not k.startswith("_")}
                existing_history.append(clean)
            session.expression_history_json = existing_history[-100:]  # Cap at 100 samples
        elif expression_data.get("imageData"):
            expression_analysis = analyze_expression(expression_data["imageData"], enforce_detection=False)
    
    if answer_type == "audio":
        if not audio_data:
            return {"error": "音频数据为空"}
        
        # Process audio: speech-to-text + audio analysis
        processed_result = process_audio_answer(audio_data)
        answer_text = processed_result["text"]
        audio_analysis = processed_result["audio_analysis"]
        
        # In chat show friendly text; full transcript used only for evaluation (stored in Evaluation)
        display_content = _normalize_candidate_display_content(
            answer_text if answer_text else ""
        )
        candidate_turn = InterviewTurn(
            session_id=session_id,
            role="candidate",
            content=display_content
        )
        db.add(candidate_turn)
        db.flush()
    else:
        # Text answer
        if not answer_text or not answer_text.strip():
            return {"error": "回答内容为空"}
        
        # Save candidate answer
        candidate_turn = InterviewTurn(
            session_id=session_id,
            role="candidate",
            content=answer_text
        )
        db.add(candidate_turn)
        db.flush()
    
    # Get current asked question
    asked_q = db.query(AskedQuestion).filter(
        AskedQuestion.session_id == session_id
    ).order_by(AskedQuestion.created_at.desc()).first()
    
    if not asked_q:
        return {"error": "未找到当前题目"}
    
    # Evaluate answer
    evaluation_result = _evaluate_answer_with_fallback(
        question=asked_q.question_text,
        correct_answer=asked_q.correct_answer_text,
        user_answer=answer_text
    )
    
    # Save evaluation - use upsert pattern with try-except for race conditions
    db.expire_all()  # Refresh session to see latest committed data
    
    existing_evaluation = db.query(Evaluation).filter(
        Evaluation.asked_question_id == asked_q.id
    ).first()
    
    if existing_evaluation:
        # Update existing evaluation
        existing_evaluation.answer_text = answer_text
        existing_evaluation.scores_json = evaluation_result["scores"]
        existing_evaluation.overall_score = evaluation_result["overall_score"]
        existing_evaluation.feedback_text = evaluation_result["feedback"]
        existing_evaluation.missing_points_json = evaluation_result["missing_points"]
        existing_evaluation.next_direction = evaluation_result["next_direction"]
        existing_evaluation.speech_analysis_json = audio_analysis
        existing_evaluation.expression_analysis_json = expression_analysis
        evaluation = existing_evaluation
    else:
        # Try to create new evaluation
        # If it fails due to duplicate key, update existing one
        try:
            evaluation = Evaluation(
                asked_question_id=asked_q.id,
                answer_text=answer_text,
                scores_json=evaluation_result["scores"],
                overall_score=evaluation_result["overall_score"],
                feedback_text=evaluation_result["feedback"],
                missing_points_json=evaluation_result["missing_points"],
                next_direction=evaluation_result["next_direction"],
                speech_analysis_json=audio_analysis,
                expression_analysis_json=expression_analysis
            )
            db.add(evaluation)
            db.flush()
        except IntegrityError as e:
            # If duplicate key error, rollback and update existing
            db.rollback()
            # Query again after rollback
            existing_evaluation = db.query(Evaluation).filter(
                Evaluation.asked_question_id == asked_q.id
            ).first()
            if existing_evaluation:
                existing_evaluation.answer_text = answer_text
                existing_evaluation.scores_json = evaluation_result["scores"]
                existing_evaluation.overall_score = evaluation_result["overall_score"]
                existing_evaluation.feedback_text = evaluation_result["feedback"]
                existing_evaluation.missing_points_json = evaluation_result["missing_points"]
                existing_evaluation.next_direction = evaluation_result["next_direction"]
                existing_evaluation.speech_analysis_json = audio_analysis
                existing_evaluation.expression_analysis_json = expression_analysis
                evaluation = existing_evaluation
            else:
                raise  # Re-raise if still can't find it
    
    db.flush()
    
    # Initialize adaptive engine
    adaptive_engine = AdaptiveInterviewEngine(db, session)
    
    # Calculate adaptive difficulty
    new_difficulty = adaptive_engine.calculate_adaptive_difficulty()
    
    # Check if should ask follow-up using adaptive algorithm
    should_followup, followup_reason = adaptive_engine.should_ask_followup(
        asked_question_id=asked_q.id,
        evaluation_score=evaluation_result["overall_score"],
        missing_points=evaluation_result.get("missing_points", [])
    )
    
    # Check if should end interview
    should_end, end_reason = adaptive_engine.should_end_interview()
    
    if should_end:
        # End interview
        return end_interview(db, session_id)
    
    if should_followup and session.current_round < session.total_rounds:
        # Generate follow-up question (LLM 优先，否则模板)
        followup_count = adaptive_engine._count_followups_for_question(asked_q.id)
        followup_content = _generate_followup(
            feedback=evaluation_result["feedback"],
            missing_points=evaluation_result.get("missing_points", []),
            original_question=asked_q.question_text,
            user_answer=answer_text or "",
            followup_count=followup_count,
            correct_answer=asked_q.correct_answer_text or "",
        )
        
        interviewer_turn = InterviewTurn(
            session_id=session_id,
            role="interviewer",
            content=followup_content
        )
        db.add(interviewer_turn)
        session.current_round += 1
        db.commit()
        
        return {
            "evaluation": evaluation_result,
            "followup": True,
            "interviewer_message": followup_content,
            "round": session.current_round,
            "followup_reason": followup_reason
        }
    else:
        # Move to next question
        # Double check if should end (adaptive check)
        should_end, end_reason = adaptive_engine.should_end_interview()
        if should_end:
            return end_interview(db, session_id)
        
        # Get resume skills and missing chapters
        resume_skills = None
        missing_chapters = []
        if session.resume_id:
            resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
            if resume and resume.parsed_json:
                resume_skills = resume.parsed_json.get("skills", [])
        
        # Collect missing chapters from evaluations
        evaluations = db.query(Evaluation).join(AskedQuestion).filter(
            AskedQuestion.session_id == session_id
        ).order_by(Evaluation.created_at.desc()).all()
        for eval_obj in evaluations:
            if eval_obj.missing_points_json:
                aq = db.query(AskedQuestion).filter(AskedQuestion.id == eval_obj.asked_question_id).first()
                if aq and aq.topic:
                    missing_chapters.append(aq.topic)
        
        # 使用最近一次评估的 next_direction 作为选题提示（LLM 输出）
        next_direction_hints = []
        if evaluations and evaluations[0].next_direction:
            next_direction_hints = [evaluations[0].next_direction]
        
        # Select next question
        next_question = select_question(
            db=db,
            session=session,
            current_difficulty=new_difficulty,
            resume_skills=resume_skills,
            missing_chapters=list(set(missing_chapters)),
            next_direction_hints=next_direction_hints
        )
        
        if not next_question:
            # No more questions, end interview
            return end_interview(db, session_id)
        
        # Create asked question
        next_asked_q = AskedQuestion(
            session_id=session_id,
            qbank_id=next_question.id,
            topic=next_question.chapter,
            difficulty=new_difficulty,
            question_text=next_question.question,
            correct_answer_text=next_question.correct_answer
        )
        db.add(next_asked_q)
        
        # Create interviewer turn (自适应过渡语)
        last_score = evaluation_result.get("overall_score")
        was_followup = adaptive_engine._count_followups_for_question(asked_q.id) > 0
        next_content = get_next_question_phrase(
            question=next_question.question,
            last_score=last_score,
            after_followup=was_followup,
            next_chapter=next_question.chapter,
        )
        interviewer_turn = InterviewTurn(
            session_id=session_id,
            role="interviewer",
            content=next_content
        )
        db.add(interviewer_turn)
        
        session.current_round += 1
        db.commit()
        
        return {
            "evaluation": evaluation_result,
            "followup": False,
            "next_question": next_question.question,
            "interviewer_message": interviewer_turn.content,
            "round": session.current_round
        }


def end_interview(db: Session, session_id: int) -> Dict:
    """End interview and generate report."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        return {"error": "面试会话不存在"}
    
    session.status = "completed"
    session.ended_at = datetime.utcnow()
    
    # Create ending turn
    ending_turn = InterviewTurn(
        session_id=session_id,
        role="interviewer",
        content="感谢你的参与！面试已结束，正在生成报告..."
    )
    db.add(ending_turn)
    db.commit()
    
    return {
        "status": "completed",
        "message": "面试已结束，请查看报告页面。"
    }


def _evaluate_answer_with_fallback(
    question: str,
    correct_answer: str,
    user_answer: str
) -> Dict:
    """Evaluate answer with LLM fallback to rules."""
    # Try LLM first
    llm_result = evaluate_with_llm(question, correct_answer, user_answer)
    
    if llm_result:
        # Retry once if validation fails
        try:
            return llm_result
        except Exception as e:
            print(f"LLM evaluation failed, retrying with rules: {e}")
    
    # Fallback to rules
    return evaluate_answer(question, correct_answer, user_answer)


def _generate_followup(
    feedback: str,
    missing_points: List[str],
    original_question: str,
    user_answer: str = "",
    followup_count: int = 0,
    correct_answer: str = "",
) -> str:
    """Generate follow-up question: LLM 优先（Misconception-Aware），否则使用多样化模板。"""
    llm_result = generate_followup_with_llm(
        original_question=original_question,
        user_answer=user_answer,
        feedback=feedback,
        missing_points=missing_points,
        followup_count=followup_count,
        correct_answer=correct_answer,
    )
    if llm_result:
        return llm_result
    return get_followup_phrase(missing_points, feedback)


def _normalize_candidate_display_content(content: str) -> str:
    """Replace voice placeholder / ASR-unconfigured text with a short friendly line for display."""
    if not content or not content.strip():
        return "（已提交语音回答）"
    s = content.strip()
    if s.startswith("[") or "需要配置语音" in s or "语音识别服务" in s or "[音频处理失败]" in s:
        return "（已提交语音回答）"
    if s.startswith("[语音回答]") and ("需要配置" in s or "语音识别" in s):
        return "（已提交语音回答）"
    return content


def get_session_turns(db: Session, session_id: int) -> List[Dict]:
    """Get all turns for a session. Candidate voice placeholders are normalized for display."""
    turns = db.query(InterviewTurn).filter(
        InterviewTurn.session_id == session_id
    ).order_by(InterviewTurn.created_at).all()
    
    return [
        {
            "id": turn.id,
            "role": turn.role,
            "content": _normalize_candidate_display_content(turn.content) if turn.role == "candidate" else turn.content,
            "created_at": turn.created_at
        }
        for turn in turns
    ]

