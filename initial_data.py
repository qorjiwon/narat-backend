import pandas as pd
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv
import os
import models
from database import engine
from uuid import uuid4

def append_csv_to_table(db_url, table_name, csv_path):
    
    # 데이터베이스 엔진 생성
    engine = create_engine(db_url)
    
    # 테이블 존재 여부 확인
    inspector = inspect(engine)
    if not table_name in inspector.get_table_names():
        print(f"테이블 '{table_name}'이 존재하지 않습니다.")
        return False
        
    # 기존 테이블의 컬럼 정보 가져오기
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    
    # CSV 파일 읽기
    print(f"CSV 파일 '{csv_path}' 읽는 중...")
    df = pd.read_csv(csv_path, encoding='utf-8', 
                     dtype={
                         "question_id": 'int',
                         "wrong_ans": 'str',
                         "correct_ans": 'str',
                         "question": 'str',
                         "explanation": 'str'
                     })
    
    # CSV 파일의 컬럼과 테이블의 컬럼 비교
    missing_columns = set(columns) - set(df.columns)
    extra_columns = set(df.columns) - set(columns)
    
    if missing_columns:
        print(f"경고: CSV 파일에 다음 컬럼이 없습니다: {missing_columns}")
        # 없는 컬럼은 NULL로 채움
        for col in missing_columns:
            df[col] = None
            
    if extra_columns:
        print(f"경고: CSV 파일에 테이블에 없는 컬럼이 있습니다. 무시됩니다: {extra_columns}")
        # 추가 컬럼 제거
        df = df[columns]
    
    for col in df.columns:
        print(df[col].dtype)
        if df[col].dtype == 'object':
            df[col] = df[col].str.replace('"', "").str.strip()
    
    # 기존 데이터 수 확인
    with engine.connect() as conn:
        conn.execute(text(f"DELETE FROM {table_name}"))
        conn.commit()
    
    # 데이터 추가
    print(f"테이블 '{table_name}'에 데이터 추가 중...")
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists='append',
        index=False,
    )
    
    # 추가된 데이터 확인
    with engine.connect() as conn:
        after_count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
    conn.commit()
    
    # test@test.com 계정 생성
    with engine.connect() as conn:
        if conn.execute(text(f"SELECT google_id FROM users WHERE email='test@test.com'")).scalar() is None:
            conn.execute(text(f"INSERT INTO users (google_id, email, display_name) VALUES ('{uuid4()}', 'test@test.com', '테스트')"))
            conn.commit()
    
    conn.commit()
    print(f"전체 행 수: {after_count}")

    return True
        

# 사용 예시
if __name__ == "__main__":
    models.Base.metadata.create_all(bind=engine)
    load_dotenv()
    # 데이터베이스 연결 정보
    DB_USER = os.environ.get("DB_ID")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = os.environ.get("DB_PORT")
    DB_NAME = os.environ.get("DB_NAME")
    
    # 데이터베이스 URL 생성
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # CSV 파일로 테이블 초기화
    append_csv_to_table(
        db_url=DATABASE_URL,
        table_name='questions',
        csv_path='problem_database.csv'
    )

