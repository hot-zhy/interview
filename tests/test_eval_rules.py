"""Test rule-based evaluation."""
from backend.services.evaluator_rules import evaluate_answer


def test_evaluate_answer_basic():
    """Test basic answer evaluation."""
    question = "What is Java?"
    correct_answer = "Java is a programming language. It is object-oriented. It runs on JVM."
    user_answer = "Java is a programming language that is object-oriented."
    
    result = evaluate_answer(question, correct_answer, user_answer)
    
    assert "scores" in result
    assert "overall_score" in result
    assert "feedback" in result
    assert "missing_points" in result
    
    scores = result["scores"]
    assert 0.0 <= scores["correctness"] <= 1.0
    assert 0.0 <= scores["depth"] <= 1.0
    assert 0.0 <= scores["clarity"] <= 1.0
    assert 0.0 <= result["overall_score"] <= 1.0


def test_evaluate_answer_complete():
    """Test evaluation of complete answer."""
    question = "Explain Java collections."
    correct_answer = "Java collections include List, Set, Map. List is ordered. Set has no duplicates. Map stores key-value pairs."
    user_answer = "Java collections include List (ordered), Set (no duplicates), and Map (key-value pairs). They are part of java.util package."
    
    result = evaluate_answer(question, correct_answer, user_answer)
    
    # Complete answer should have high scores
    assert result["overall_score"] > 0.7
    assert result["scores"]["correctness"] > 0.7


def test_evaluate_answer_incomplete():
    """Test evaluation of incomplete answer."""
    question = "What is Spring Framework?"
    correct_answer = "Spring is a framework. It provides IoC container. It supports AOP. It simplifies enterprise development."
    user_answer = "Spring is a framework."
    
    result = evaluate_answer(question, correct_answer, user_answer)
    
    # Incomplete answer should have lower scores
    assert result["overall_score"] < 0.7
    assert len(result["missing_points"]) > 0


def test_evaluate_answer_structure():
    """Test evaluation considers answer structure."""
    question = "Compare ArrayList and LinkedList."
    correct_answer = "ArrayList uses array. LinkedList uses linked nodes. ArrayList is faster for random access. LinkedList is faster for insertions."
    user_answer = """
    1. ArrayList uses array internally
    2. LinkedList uses linked nodes
    3. ArrayList is faster for random access
    4. LinkedList is faster for insertions
    """
    
    result = evaluate_answer(question, correct_answer, user_answer)
    
    # Well-structured answer should have high clarity
    assert result["scores"]["clarity"] > 0.6

