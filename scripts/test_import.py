"""Test script to debug question import."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from backend.db.base import get_db, engine
from backend.db.models import QuestionBank
from backend.services.question_bank_loader import import_questions_from_excel
import pandas as pd

def test_import():
    """Test importing questions."""
    print("="*60)
    print("测试题库导入功能")
    print("="*60)
    
    # Check if file exists
    file_path = "data/question.xlsx"
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return
    
    print(f"✅ 找到文件: {file_path}")
    
    # Read Excel to check content
    try:
        df = pd.read_excel(file_path)
        print(f"\nExcel 文件信息:")
        print(f"  总行数: {len(df)}")
        print(f"  列名: {df.columns.tolist()}")
        
        # Check first few rows
        print(f"\n前3行数据预览:")
        for idx in range(min(3, len(df))):
            row = df.iloc[idx]
            print(f"  行 {idx+1}:")
            print(f"    id: {row.get('id', 'N/A')} (type: {type(row.get('id'))})")
            print(f"    question: {str(row.get('question', 'N/A'))[:50]}...")
            print(f"    difficulty: {row.get('difficulty', 'N/A')} (isna: {pd.isna(row.get('difficulty', 'N/A'))})")
            print(f"    chapter: {str(row.get('chapter', 'N/A'))[:30]}...")
    except Exception as e:
        print(f"❌ 读取 Excel 失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check current count
        initial_count = db.query(QuestionBank).count()
        print(f"\n当前数据库中的题目数: {initial_count}")
        
        # Import questions
        print(f"\n开始导入...")
        result = import_questions_from_excel(db, file_path)
        
        print(f"\n导入结果:")
        print(f"  总计: {result.total}")
        print(f"  新增: {result.created}")
        print(f"  更新: {result.updated}")
        print(f"  跳过: {result.skipped}")
        print(f"  失败: {result.failed}")
        
        if result.errors:
            print(f"\n错误信息 (前10条):")
            for error in result.errors[:10]:
                print(f"  - {error}")
        
        # Check final count
        db.expire_all()
        final_count = db.query(QuestionBank).count()
        print(f"\n导入后数据库中的题目数: {final_count}")
        print(f"实际增加: {final_count - initial_count}")
        
        # Try to query a few questions
        if final_count > 0:
            print(f"\n查询前3条题目:")
            questions = db.query(QuestionBank).limit(3).all()
            for q in questions:
                print(f"  ID: {q.id}, 题目: {q.question[:50]}..., 难度: {q.difficulty}, 章节: {q.chapter}")
        
    except Exception as e:
        print(f"\n❌ 导入过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_import()

