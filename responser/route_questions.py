from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import datetime
from models.models import QuestionDB, CategoryDB
from dbmanage import get_db
from sqlalchemy.orm import Session
from uuid import uuid4
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
import random

header = "/api/questions"
router = APIRouter(
    prefix = header,
    tags   = ['questions']
)

@router.get('/')
async def get_questions(
    category_id: Optional[int] = None,
    difficulty_level: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    문제 목록을 조회합니다.
    """
    query = db.query(QuestionDB)
    
    if category_id is not None:
        query = query.filter(QuestionDB.category_id == category_id)
    
    if difficulty_level is not None:
        query = query.filter(QuestionDB.difficulty_level == difficulty_level)
    
    total = query.count()
    questions = query.offset(offset).limit(limit).all()
    
    result = []
    for question in questions:
        result.append({
            "question_id": question.question_id,
            "category_id": question.category_id,
            "wrong_sentence": question.wrong_sentence,
            "right_sentence": question.right_sentence,
            "wrong_word": question.wrong_word,
            "right_word": question.right_word,
            "location": question.location,
            "difficulty_level": question.difficulty_level,
            "explanation": question.explanation,
            "is_active": question.is_active,
            "total_attempts": question.total_attempts,
            "correct_rate": question.correct_rate,
            "avg_time_spent": question.avg_time_spent,
            "dropout_rate": question.dropout_rate
        })
    
    return JSONResponse({
        "success": True,
        "questions": result,
        "total": total
    })

@router.get('/{question_id}')
async def get_question(question_id: int, db: Session = Depends(get_db)):
    """
    특정 문제의 상세 정보를 조회합니다.
    """
    question = db.query(QuestionDB).filter(QuestionDB.question_id == question_id).first()
    
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    
    return JSONResponse({
        "success": True,
        "question": {
            "question_id": question.question_id,
            "category_id": question.category_id,
            "wrong_sentence": question.wrong_sentence,
            "right_sentence": question.right_sentence,
            "wrong_word": question.wrong_word,
            "right_word": question.right_word,
            "location": question.location,
            "difficulty_level": question.difficulty_level,
            "explanation": question.explanation,
            "is_active": question.is_active,
            "total_attempts": question.total_attempts,
            "correct_rate": question.correct_rate,
            "avg_time_spent": question.avg_time_spent,
            "dropout_rate": question.dropout_rate,
            "daily_stats": question.daily_stats,
            "stats_updated_at": question.stats_updated_at,
            "created_at": question.created_at
        }
    })

@router.get('/random')
async def get_random_question(
    category_id: Optional[int] = None,
    difficulty_level: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    랜덤 문제를 조회합니다.
    """
    query = db.query(QuestionDB)
    
    if category_id is not None:
        query = query.filter(QuestionDB.category_id == category_id)
    
    if difficulty_level is not None:
        query = query.filter(QuestionDB.difficulty_level == difficulty_level)
    
    questions = query.all()
    
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found")
    
    question = random.choice(questions)
    
    return JSONResponse({
        "success": True,
        "question": {
            "question_id": question.question_id,
            "category_id": question.category_id,
            "wrong_sentence": question.wrong_sentence,
            "right_sentence": question.right_sentence,
            "wrong_word": question.wrong_word,
            "right_word": question.right_word,
            "location": question.location,
            "difficulty_level": question.difficulty_level,
            "explanation": question.explanation
        }
    })

