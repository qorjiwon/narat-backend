from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models.models import CategoryDB, QuestionDB
from dbmanage import get_db
from typing import List, Optional

header = "/api/categories"
router = APIRouter(
    prefix = header,
    tags   = ['categories']
)

@router.get('/')
async def get_categories(db: Session = Depends(get_db)):
    """
    카테고리 목록을 조회합니다.
    """
    categories = db.query(CategoryDB).all()
    
    result = []
    for category in categories:
        result.append({
            "category_id": category.category_id,
            "name": category.name,
            "description": category.description,
            "question_count": db.query(QuestionDB).filter(
                QuestionDB.category_id == category.category_id
            ).count()
        })
    
    return JSONResponse({
        "success": True,
        "categories": result
    })

@router.get('/{category_id}')
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """
    특정 카테고리의 상세 정보를 조회합니다.
    """
    category = db.query(CategoryDB).filter(CategoryDB.category_id == category_id).first()
    
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    question_count = db.query(QuestionDB).filter(
        QuestionDB.category_id == category_id
    ).count()
    
    return JSONResponse({
        "success": True,
        "category": {
            "category_id": category.category_id,
            "name": category.name,
            "description": category.description,
            "question_count": question_count
        }
    })

@router.get('/{category_id}/questions')
async def get_category_questions(
    category_id: int,
    difficulty_level: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    특정 카테고리의 문제 목록을 조회합니다.
    """
    category = db.query(CategoryDB).filter(CategoryDB.category_id == category_id).first()
    
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    query = db.query(QuestionDB).filter(QuestionDB.category_id == category_id)
    
    if difficulty_level is not None:
        query = query.filter(QuestionDB.difficulty_level == difficulty_level)
    
    total = query.count()
    questions = query.offset(offset).limit(limit).all()
    
    result = []
    for question in questions:
        result.append({
            "question_id": question.question_id,
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
        "category": {
            "category_id": category.category_id,
            "name": category.name,
            "description": category.description
        },
        "questions": result,
        "total": total
    }) 