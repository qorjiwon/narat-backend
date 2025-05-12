import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Base, CategoryDB, QuestionDB
from database import SQLALCHEMY_DATABASE_URL

# 데이터베이스 연결
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 테이블 생성
Base.metadata.create_all(bind=engine)

def migrate_data():
    # CSV 파일 읽기
    df = pd.read_csv('problem_database_fin.csv')
    
    # 세션 생성
    db = SessionLocal()
    
    try:
        # 카테고리 데이터 삽입
        categories = {
            0: "문법적으로 틀린 단어/구절",
            1: "용례가 다른 단어/구절",
            2: "띄어쓰기 문제"
        }
        
        for category_id, description in categories.items():
            category = CategoryDB(
                category_id=category_id,
                name=f"Category {category_id}",
                description=description
            )
            db.add(category)
        
        db.commit()
        
        # 문제 데이터 삽입
        for _, row in df.iterrows():
            question = QuestionDB(
                question_id=row['item_id'],
                category_id=row['category'],
                wrong_sentence=row['Wrong_S'].strip('" '),
                right_sentence=row['Right_S'].strip('" '),
                wrong_word=row['Wrong_W'].strip('" '),
                right_word=row['Right_W'].strip('" '),
                location=row['loc'].strip('" '),
                difficulty_level=row['difficulty'],
                explanation=row['reason']
            )
            db.add(question)
        
        db.commit()
        print("데이터 마이그레이션이 성공적으로 완료되었습니다.")
        
    except Exception as e:
        print(f"에러 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data() 