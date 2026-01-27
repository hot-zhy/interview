"""Question bank loader service."""
import pandas as pd
from typing import List, Tuple
from sqlalchemy.orm import Session
from backend.db.models import QuestionBank
from backend.schemas.question import ImportResult


def validate_excel_header(df: pd.DataFrame) -> bool:
    """Validate Excel header matches required format."""
    required_columns = ['id', 'question', 'correct_answer', 'difficulty', 'chapter']
    return all(col in df.columns for col in required_columns)


def import_questions_from_excel(
    db: Session,
    file_path: str,
    min_difficulty: int = 1,
    max_difficulty: int = 5
) -> ImportResult:
    """
    Import questions from Excel file.
    
    Returns ImportResult with statistics.
    """
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return ImportResult(
            total=0,
            created=0,
            updated=0,
            skipped=0,
            failed=0,
            errors=[f"Failed to read Excel file: {str(e)}"]
        )
    
    # Validate header
    if not validate_excel_header(df):
        return ImportResult(
            total=len(df),
            created=0,
            updated=0,
            skipped=0,
            failed=len(df),
            errors=["Excel header must contain: id, question, correct_answer, difficulty, chapter"]
        )
    
    created = 0
    updated = 0
    skipped = 0
    failed = 0
    errors = []
    
    print(f"Total rows in Excel: {len(df)}")
    print(f"Excel columns: {df.columns.tolist()}")
    
    # Count rows with missing difficulty
    if 'difficulty' in df.columns:
        missing_difficulty = df['difficulty'].isna().sum()
        if missing_difficulty > 0:
            print(f"Warning: {missing_difficulty} rows have missing difficulty, will use default value 3")
    
    for idx, row in df.iterrows():
        try:
            # Validate required fields
            q_id = str(row['id']).strip()
            if not q_id or pd.isna(q_id) or q_id == 'nan':
                skipped += 1
                if skipped <= 5:  # Debug first few skips
                    print(f"Row {idx + 2}: Skipping - id is empty or invalid: {q_id}")
                errors.append(f"Row {idx + 2}: id is empty")
                continue
            
            question = str(row['question']).strip()
            if not question or pd.isna(question) or question == 'nan':
                skipped += 1
                if skipped <= 5:
                    print(f"Row {idx + 2}: Skipping - question is empty")
                errors.append(f"Row {idx + 2}: question is empty")
                continue
            
            correct_answer = str(row['correct_answer']).strip()
            if not correct_answer or pd.isna(correct_answer) or correct_answer == 'nan':
                skipped += 1
                if skipped <= 5:
                    print(f"Row {idx + 2}: Skipping - correct_answer is empty")
                errors.append(f"Row {idx + 2}: correct_answer is empty")
                continue
            
            chapter = str(row['chapter']).strip()
            # Remove newlines and extra whitespace
            chapter = ' '.join(chapter.split())
            if not chapter or pd.isna(chapter) or chapter == 'nan':
                skipped += 1
                errors.append(f"Row {idx + 2}: chapter is empty")
                continue
            
            # Validate and clamp difficulty
            # If difficulty is missing, use default value (3 = medium)
            try:
                if pd.isna(row['difficulty']):
                    difficulty = 3  # Default to medium difficulty
                else:
                    difficulty = int(float(row['difficulty']))
                    if difficulty < min_difficulty:
                        difficulty = min_difficulty
                    elif difficulty > max_difficulty:
                        difficulty = max_difficulty
            except (ValueError, TypeError) as e:
                # If conversion fails, use default
                difficulty = 3
                print(f"Row {idx + 2}: difficulty conversion failed, using default 3: {e}")
            
            # Upsert question
            existing = db.query(QuestionBank).filter(QuestionBank.id == q_id).first()
            
            if existing:
                existing.question = question
                existing.correct_answer = correct_answer
                existing.difficulty = difficulty
                existing.chapter = chapter
                updated += 1
                if updated <= 3:  # Debug first few
                    print(f"Updating question {q_id}: {question[:50]}...")
            else:
                new_question = QuestionBank(
                    id=q_id,
                    question=question,
                    correct_answer=correct_answer,
                    difficulty=difficulty,
                    chapter=chapter
                )
                db.add(new_question)
                created += 1
                if created <= 3:  # Debug first few
                    print(f"Creating question {q_id}: {question[:50]}...")
            
        except Exception as e:
            failed += 1
            errors.append(f"Row {idx + 2}: {str(e)}")
    
    print(f"\nBefore commit: created={created}, updated={updated}, skipped={skipped}, failed={failed}")
    
    try:
        db.commit()
        # Verify commit by checking count
        db.expire_all()  # Refresh session
        verify_count = db.query(QuestionBank).count()
        print(f"After commit: {created} created, {updated} updated, total in DB: {verify_count}")
        
        if created == 0 and updated == 0 and skipped == 0 and failed == 0:
            print("WARNING: No records processed! Check validation logic.")
            print(f"Total rows in Excel: {len(df)}")
            print(f"Sample row 0: id={df.iloc[0]['id']}, question={str(df.iloc[0]['question'])[:30]}...")
    except Exception as e:
        db.rollback()
        print(f"Commit failed: {e}")
        import traceback
        traceback.print_exc()
        return ImportResult(
            total=len(df),
            created=0,
            updated=0,
            skipped=skipped,
            failed=len(df) - skipped,
            errors=[f"Database commit failed: {str(e)}"] + errors
        )
    
    return ImportResult(
        total=len(df),
        created=created,
        updated=updated,
        skipped=skipped,
        failed=failed,
        errors=errors[:50]  # Limit errors to first 50
    )

