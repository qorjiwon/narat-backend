from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import datetime
from models.models import RecommendationsDB, RecommendationQuestionsDB, QuestionDB, UserLogDB, SessionDB
from dbmanage import get_db
from sqlalchemy.orm import Session
from uuid import uuid4
import os
from dotenv import load_dotenv
import torch
from models.sasrec import SasRecRecommender
from typing import List, Dict, Optional

header = "/api/recommendations"
router = APIRouter(
    prefix = header,
    tags   = ['recommendations']
)

load_dotenv()

# 전역 변수로 SasRec 모델 인스턴스 생성
recommender = None

def get_recommender(db: Session) -> SasRecRecommender:
    global recommender
    if recommender is None:
        # 전체 문제 수 가져오기
        num_items = db.query(QuestionDB).count()
        recommender = SasRecRecommender(num_items=num_items)
    return recommender

class RecommendationsForm(BaseModel):
    session_token: str

@router.post('/')
async def create_recommendation(item: RecommendationsForm, db: Session = Depends(get_db)):
    """
    새로운 추천을 생성합니다.
    """
    data_session = db.query(SessionDB).filter(SessionDB.session_id == item.session_token).first()
    if data_session is None:
        raise HTTPException(status_code=403, detail="User not found")   
    
    log_data = db.query(UserLogDB).filter(UserLogDB.google_id == data_session.google_id).all()
    if len(log_data) < 30:
        rec_type = 1  # less than 30
    else:
        rec_type = 2  # more than 30

    data = RecommendationsDB(rec_id=str(uuid4()), google_id=data_session.google_id, rec_type=rec_type)
    db.add(data)
    db.commit()

    return JSONResponse({"rec_id": data.rec_id})

class RecommendationsSuccessForm(BaseModel):
    rec_id: str

@router.post('/success')
async def get_recommendation(item: RecommendationsSuccessForm, db: Session = Depends(get_db)):
    """
    추천 결과를 가져옵니다.
    """
    data = db.query(RecommendationsDB).filter(RecommendationsDB.rec_id == item.rec_id).first()
    if data is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    if data.rec_status:
        result_data = []
        data_rec = db.query(RecommendationQuestionsDB).filter(
            RecommendationQuestionsDB.rec_id == item.rec_id
        ).order_by(RecommendationQuestionsDB.order).all()
        
        if len(data_rec) == 0:
            raise HTTPException(status_code=404, detail="Recommendation questions is empty")
            
        for row in data_rec:
            data_question = db.query(QuestionDB).filter(
                QuestionDB.question_id == row.question_id
            ).first()
            result_data.append({
                "question_id": row.question_id,
                "wrong_sentence": data_question.wrong_sentence,
                "right_sentence": data_question.right_sentence,
                "wrong_word": data_question.wrong_word,
                "right_word": data_question.right_word,
                "location": data_question.location,
                "difficulty_level": data_question.difficulty_level,
                "explanation": data_question.explanation
            })

    else:
        data.rec_status = True
        db.commit()

        # 사용자의 학습 기록 가져오기
        log_data = db.query(UserLogDB).filter(
            UserLogDB.google_id == data.google_id
        ).order_by(UserLogDB.created_at).all()
        
        # 학습 시퀀스 생성 (문제 ID만 사용)
        sequence = [log.question_id for log in log_data]
        
        # SasRec 모델을 사용한 추천
        recommender = get_recommender(db)
        recommendations = recommender.recommend(sequence, top_k=10)
        
        # 추천 결과 저장
        result_data = []
        for idx, (question_id, score) in enumerate(recommendations):
            question = db.query(QuestionDB).filter(
                QuestionDB.question_id == question_id
            ).first()
            
            result_data.append({
                "question_id": question.question_id,
                "wrong_sentence": question.wrong_sentence,
                "right_sentence": question.right_sentence,
                "wrong_word": question.wrong_word,
                "right_word": question.right_word,
                "location": question.location,
                "difficulty_level": question.difficulty_level,
                "explanation": question.explanation
            })
            
            data_rec = RecommendationQuestionsDB(
                rec_id=data.rec_id,
                question_id=question_id,
                order=idx
            )
            db.add(data_rec)
        
        db.commit()

    return JSONResponse({
        "success": True,
        "recommendation": result_data
    })

@router.get('/')
async def get_recommendations(
    google_id: str,
    limit: int = Query(5, ge=1, le=20),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    사용자의 추천 목록을 조회합니다.
    """
    recommendations = db.query(RecommendationsDB).filter(
        RecommendationsDB.google_id == google_id
    ).order_by(RecommendationsDB.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for rec in recommendations:
        result.append({
            "rec_id": rec.rec_id,
            "rec_status": rec.rec_status,
            "rec_type": rec.rec_type,
            "created_at": rec.created_at
        })
    
    return JSONResponse({
        "success": True,
        "recommendations": result
    })

@router.get('/{rec_id}')
async def get_recommendation_detail(rec_id: str, db: Session = Depends(get_db)):
    """
    특정 추천의 상세 정보를 조회합니다.
    """
    recommendation = db.query(RecommendationsDB).filter(
        RecommendationsDB.rec_id == rec_id
    ).first()
    
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    return JSONResponse({
        "success": True,
        "recommendation": {
            "rec_id": recommendation.rec_id,
            "google_id": recommendation.google_id,
            "rec_status": recommendation.rec_status,
            "rec_type": recommendation.rec_type,
            "created_at": recommendation.created_at
        }
    }) 