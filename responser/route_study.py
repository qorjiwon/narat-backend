from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import datetime
import models
from dbmanage import get_db
from sqlalchemy.orm import Session
from uuid import uuid4
import os
from dotenv import load_dotenv
from sqlalchemy import func, case

header = "/api/study"
router = APIRouter(
    prefix = header,
    tags   = ['study']
)

@router.get('/')
async def root():
    return {"success": "true"}

class StudySubmitForm(BaseModel):
    session_token: str
    question_id: int
    correct: bool
    delaytime: float = 0.0  # 문제 풀이 시간 (초 단위)

def update_study_level(db: Session, google_id: str):
    """
    사용자의 최근 30문제 학습 기록을 기반으로 study level을 업데이트합니다.
    정답률과 평균 풀이 시간을 기준으로 'S', 'A', 'B' 레벨을 결정합니다.
    """
    # 최근 30문제의 학습 기록을 가져옵니다
    recent_logs = db.query(models.UserLogDB).filter(
        models.UserLogDB.google_id == google_id
    ).order_by(
        models.UserLogDB.created_at.desc()
    ).limit(30).all()

    if len(recent_logs) < 10:  # 최소 10문제 이상 풀어야 레벨 평가
        return 'B'

    # 정답률 계산
    correct_count = sum(1 for log in recent_logs if log.correct)
    correct_rate = correct_count / len(recent_logs)

    # 평균 풀이 시간 계산 (초 단위)
    avg_time = sum(log.delaytime for log in recent_logs) / len(recent_logs)

    # 레벨 결정 기준
    if correct_rate >= 0.8 and avg_time <= 3.0:  # 80% 이상 정답률, 3초 이하 평균 시간
        return 'S'
    elif correct_rate >= 0.6 and avg_time <= 5.0:  # 60% 이상 정답률, 5초 이하 평균 시간
        return 'A'
    else:
        return 'B'

@router.post('/submit')
async def submit(item: StudySubmitForm, db: Session = Depends(get_db)):
    data_session = db.query(models.SessionDB).filter(models.SessionDB.session_token == item.session_token).first()
    if data_session is None:
        raise HTTPException(status_code=403, detail="User not found")   

    data_problem = db.query(models.QuestionDB).filter(models.QuestionDB.question_id == item.question_id).first()
    if data_problem is None:
        raise HTTPException(status_code=404, detail="Question not found")

    # 학습 기록 저장
    data = models.UserLogDB(
        google_id=data_session.google_id,
        question_id=item.question_id,
        correct=item.correct,
        delaytime=item.delaytime if hasattr(item, 'delaytime') else 0.0
    )
    db.add(data)
    db.commit()

    # study level 업데이트
    new_level = update_study_level(db, data_session.google_id)
    user = db.query(models.UserDB).filter(models.UserDB.google_id == data_session.google_id).first()
    if user and user.study_level != new_level:
        user.study_level = new_level
        db.commit()

    return JSONResponse({
        "success": "true",
        "explanation": data_problem.explanation,
        "study_level": new_level
    })

class StudyHistoryForm(BaseModel):
    session_token: str
    limit: int = 10

@router.post('/recent-history')
async def get_recent_history(item: StudyHistoryForm, db: Session = Depends(get_db)):
    data_session = db.query(models.SessionDB).filter(models.SessionDB.session_token == item.session_token).first()
    if data_session is None:
        raise HTTPException(status_code=403, detail="User not found")   

    # 최근 학습 기록
    recent_logs = db.query(models.UserLogDB, models.QuestionDB).join(
        models.QuestionDB,
        models.UserLogDB.question_id == models.QuestionDB.question_id
    ).filter(
        models.UserLogDB.google_id == data_session.google_id
    ).order_by(
        models.UserLogDB.created_at.desc()
    ).limit(item.limit).all()

    # 시간 통계
    time_stats = db.query(
        func.avg(models.UserLogDB.delaytime).label('avg_time'),
        func.sum(models.UserLogDB.delaytime).label('total_time'),
        func.count(models.UserLogDB.log_id).label('total_questions')
    ).filter(
        models.UserLogDB.google_id == data_session.google_id
    ).first()

    # 결과 포맷팅
    history_result = []
    for log, question in recent_logs:
        history_result.append({
            "question_id": question.question_id,
            "wrong_sentence": question.wrong_sentence,
            "right_sentence": question.right_sentence,
            "correct": log.correct,
            "time_spent": round(log.delaytime, 2),
            "created_at": log.created_at.isoformat()
        })

    return JSONResponse({
        "recent_history": history_result,
        "time_stats": {
            "average_time": round(time_stats.avg_time, 2) if time_stats.avg_time else 0,
            "total_time": round(time_stats.total_time, 2) if time_stats.total_time else 0,
            "total_questions": time_stats.total_questions
        }
    })

class RecentWrongAnswersForm(BaseModel):
    session_token: str
    limit: int = 5

@router.post('/recent-wrong')
async def get_recent_wrong_answers(item: RecentWrongAnswersForm, db: Session = Depends(get_db)):
    data_session = db.query(models.SessionDB).filter(models.SessionDB.session_token == item.session_token).first()
    if data_session is None:
        raise HTTPException(status_code=403, detail="User not found")   

    # 최근에 틀린 문제들을 가져옵니다
    wrong_answers = db.query(models.UserLogDB, models.QuestionDB).join(
        models.QuestionDB,
        models.UserLogDB.question_id == models.QuestionDB.question_id
    ).filter(
        models.UserLogDB.google_id == data_session.google_id,
        models.UserLogDB.correct == False
    ).order_by(
        models.UserLogDB.created_at.desc()
    ).limit(item.limit).all()

    result = []
    for log, question in wrong_answers:
        result.append({
            "wrong_sentence": question.wrong_sentence,
            "right_sentence": question.right_sentence,
            "wrong_word": question.wrong_word,
            "right_word": question.right_word,
            "explanation": question.explanation,
            "created_at": log.created_at.isoformat()
        })

    return JSONResponse({"recent_wrong_answers": result})

class StudyStatsForm(BaseModel):
    session_token: str

@router.post('/stats')
async def get_study_stats(item: StudyStatsForm, db: Session = Depends(get_db)):
    data_session = db.query(models.SessionDB).filter(models.SessionDB.session_token == item.session_token).first()
    if data_session is None:
        raise HTTPException(status_code=403, detail="User not found")   

    # 카테고리별 통계
    category_stats = db.query(
        models.CategoryDB.name,
        func.count(models.UserLogDB.log_id).label('total'),
        func.sum(case((models.UserLogDB.correct == True, 1), else_=0)).label('correct')
    ).join(
        models.QuestionDB,
        models.QuestionDB.category_id == models.CategoryDB.category_id
    ).join(
        models.UserLogDB,
        models.UserLogDB.question_id == models.QuestionDB.question_id
    ).filter(
        models.UserLogDB.google_id == data_session.google_id
    ).group_by(
        models.CategoryDB.name
    ).all()

    # 난이도별 통계
    difficulty_stats = db.query(
        models.QuestionDB.difficulty_level,
        func.count(models.UserLogDB.log_id).label('total'),
        func.sum(case((models.UserLogDB.correct == True, 1), else_=0)).label('correct')
    ).join(
        models.UserLogDB,
        models.UserLogDB.question_id == models.QuestionDB.question_id
    ).filter(
        models.UserLogDB.google_id == data_session.google_id
    ).group_by(
        models.QuestionDB.difficulty_level
    ).all()

    # 결과 포맷팅
    category_result = []
    for name, total, correct in category_stats:
        category_result.append({
            "category": name,
            "total": total,
            "correct": correct,
            "correct_rate": round((correct / total) * 100, 2) if total > 0 else 0
        })

    difficulty_result = []
    for level, total, correct in difficulty_stats:
        difficulty_result.append({
            "level": level,
            "total": total,
            "correct": correct,
            "correct_rate": round((correct / total) * 100, 2) if total > 0 else 0
        })

    return JSONResponse({
        "category_stats": category_result,
        "difficulty_stats": difficulty_result
    })