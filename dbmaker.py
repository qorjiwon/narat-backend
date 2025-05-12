# -*- coding: utf-8 -*-

import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine
import sys
from dotenv import load_dotenv
import os

def create_database(db_name, user, password, host='localhost', port='5432'):
    """PostgreSQL 데이터베이스를 자동으로 생성하는 함수"""
    conn = psycopg2.connect(
        dbname='postgres', 
        user=user, 
        password=password, 
        host=host, 
        port=port
    )
    conn.set_client_encoding('UTF8')
    conn.autocommit = True  # 자동 커밋 활성화
    
    cursor = conn.cursor()
    
    cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [db_name])
    exists = cursor.fetchone()
    
    if not exists:
        cursor.execute(sql.SQL("CREATE DATABASE {}".format(db_name)))
        print(f"데이터베이스 '{db_name}'가 생성되었습니다.")
    else:
        print(f"데이터베이스 '{db_name}'가 이미 존재합니다. 정말로 초기화하시겠습니까? (Y/n):")
        if input() == 'Y':
            cursor.execute(sql.SQL("DROP DATABASE {}".format(db_name)))
            cursor.execute(sql.SQL("CREATE DATABASE {}".format(db_name)))

    
    cursor.close()
    conn.close()
    
def init_database():
    """데이터베이스 초기화 및 SQLAlchemy 설정"""
    # 데이터베이스 접속 정보
    DB_USER = os.environ.get("DB_ID")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = os.environ.get("DB_PORT")
    DB_NAME = os.environ.get("DB_NAME")
    
    # 데이터베이스 생성
    create_database(DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
    
    # SQLAlchemy 엔진 생성
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(DATABASE_URL)
    
    return engine

if __name__ == "__main__":
    os.environ["PYTHONIOENCODING"] = "UTF-8"
    load_dotenv()
    init_database()
    print("데이터베이스 초기화가 완료되었습니다.")