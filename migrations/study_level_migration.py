from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 데이터베이스 연결 정보
DATABASE_URL = os.getenv("DATABASE_URL")

def migrate_study_level():
    """
    study_level 필드를 Integer에서 String으로 변경하고,
    기존 사용자들의 study level을 'B'로 초기화합니다.
    """
    # 데이터베이스 연결
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 1. 기존 study_level 값을 백업
        db.execute(text("""
            ALTER TABLE users 
            ADD COLUMN study_level_backup INTEGER;
            
            UPDATE users 
            SET study_level_backup = study_level;
        """))

        # 2. study_level 컬럼 타입 변경
        db.execute(text("""
            ALTER TABLE users 
            ALTER COLUMN study_level TYPE VARCHAR(1);
            
            UPDATE users 
            SET study_level = 'B';
        """))

        # 3. 백업 컬럼 삭제
        db.execute(text("""
            ALTER TABLE users 
            DROP COLUMN study_level_backup;
        """))

        db.commit()
        print("Study level 마이그레이션이 성공적으로 완료되었습니다.")

    except Exception as e:
        db.rollback()
        print(f"마이그레이션 중 오류 발생: {str(e)}")
        raise

    finally:
        db.close()

if __name__ == "__main__":
    migrate_study_level() 