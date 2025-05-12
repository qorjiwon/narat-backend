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
import random
import numpy as np
from collections import defaultdict

header = "/api/recommendations"
router = APIRouter(
    prefix = header,
    tags   = ['recommendations']
)

load_dotenv()

class RecommendationsForm(BaseModel):
    session_token: str

@router.post('/')
async def root(item: RecommendationsForm, db: Session = Depends(get_db)):
    data_session = db.query(models.SessionDB).filter(models.SessionDB.session_id == item.session_token).first()
    if data_session is None:
        raise HTTPException(status_code=403, detail="User not found")   
    
    log_data = db.query(models.UserLogDB).filter(models.UserLogDB.google_id == data_session.google_id).all()
    if len(log_data) < 30:
        rec_type = 1 # less than 30
    else:
        rec_type = 2 # more than 30

    data = models.RecommendationsDB(rec_id=str(uuid4()), google_id=data_session.google_id, rec_type=rec_type)

    db.add(data)
    db.commit()

    return JSONResponse({"rec_id": data.rec_id})

class RecommendationsSuccessForm(BaseModel):
    rec_id: str

@router.post('/success')
async def root(item: RecommendationsSuccessForm, db: Session = Depends(get_db)):
    data = db.query(models.RecommendationsDB).filter(models.RecommendationsDB.rec_id == item.rec_id).first()
    if data is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    if data.rec_status:
        result_data = []
        data_rec = db.query(models.RecommendationQuestionsDB).filter(models.RecommendationQuestionsDB.rec_id == item.rec_id).order_by(models.RecommendationQuestionsDB.order).all()
        if len(data_rec) == 0:
            raise HTTPException(status_code=404, detail="Recommendation questions is empty")
        for row in data_rec:
            data_question = db.query(models.QuestionDB).filter(models.QuestionDB.question_id == row.question_id).first()
            result_data.append({
                "question_id": row.question_id,
                "question": data_question.question,
                "wrong_ans": data_question.wrong_ans,
                "correct_ans": data_question.correct_ans,
                "explanation": data_question.explanation
            })

    else:
        data.rec_status = True
        db.commit()

        # SSREF 알고리즘 구현
        # 1. 모든 문제 가져오기
        all_questions = db.query(models.QuestionDB).all()
        
        # 2. 사용자의 학습 기록 가져오기 (시간순 정렬)
        log_data = db.query(models.UserLogDB).filter(models.UserLogDB.google_id == data.google_id).order_by(models.UserLogDB.created_at).all()
        
        # 3. 사용자가 이미 풀었던 문제 ID 목록
        solved_question_ids = [log.question_id for log in log_data]
        
        # 4. 추천할 문제 수
        num_recommendations = 5
        
        # 5. SSREF 알고리즘 적용
        recommended_questions = ssref_algorithm(db, data.google_id, log_data, all_questions, solved_question_ids, num_recommendations, data.rec_type)
        
        # 6. 추천 문제 저장
        result_data = []
        for idx, question in enumerate(recommended_questions):
            result_data.append({
                "question_id": question.question_id,
                "question": question.question,
                "wrong_ans": question.wrong_ans,
                "correct_ans": question.correct_ans,
                "explanation": question.explanation
            })
            
            data_rec = models.RecommendationQuestionsDB(rec_id=data.rec_id, question_id=question.question_id, order=idx)
            db.add(data_rec)
        
        db.commit()

    return JSONResponse({"success": True,
                         "recommendation": result_data})

def ssref_algorithm(db, google_id, log_data, all_questions, solved_question_ids, num_recommendations, rec_type):
    """
    SSREF (Sequential Self-Refinement) 알고리즘을 적용한 추천 시스템
    
    Args:
        db: 데이터베이스 세션
        google_id: 사용자 ID
        log_data: 사용자의 학습 기록
        all_questions: 모든 문제 목록
        solved_question_ids: 사용자가 이미 풀었던 문제 ID 목록
        num_recommendations: 추천할 문제 수
        rec_type: 추천 유형 (1: 초기 추천, 2: 후속 추천)
        
    Returns:
        추천된 문제 목록
    """
    # 1. 사용자 정보 가져오기
    user = db.query(models.UserDB).filter(models.UserDB.google_id == google_id).first()
    study_level = user.study_level if user else 1
    
    # 2. 문제 난이도 및 주제 정보 가져오기 (실제 구현에서는 문제 모델에 난이도와 주제 필드 추가 필요)
    # 여기서는 임의로 난이도와 주제를 생성
    question_difficulty = {q.question_id: random.randint(1, 5) for q in all_questions}
    question_topic = {q.question_id: random.randint(1, 3) for q in all_questions}
    
    # 3. 사용자의 학습 패턴 분석
    if len(log_data) > 0:
        # 3.1 시간 기반 가중치 계산 (최근 기록에 더 높은 가중치)
        time_weights = calculate_time_weights(log_data)
        
        # 3.2 성공/실패 패턴 분석
        success_patterns = analyze_success_patterns(log_data, time_weights)
        
        # 3.3 주제별 성공률 분석
        topic_success_rate = analyze_topic_success_rate(log_data, question_topic, time_weights)
        
        # 3.4 난이도별 성공률 분석
        difficulty_success_rate = analyze_difficulty_success_rate(log_data, question_difficulty, time_weights)
    else:
        # 학습 기록이 없는 경우 기본값 설정
        success_patterns = {}
        topic_success_rate = {1: 0.5, 2: 0.5, 3: 0.5}
        difficulty_success_rate = {1: 0.5, 2: 0.5, 3: 0.5, 4: 0.5, 5: 0.5}
    
    # 4. 문제 점수 계산
    question_scores = calculate_question_scores(
        all_questions, 
        solved_question_ids, 
        question_difficulty, 
        question_topic, 
        study_level, 
        topic_success_rate, 
        difficulty_success_rate,
        rec_type
    )
    
    # 5. 상위 N개 문제 선택
    recommended_questions = select_top_n_questions(question_scores, num_recommendations)
    
    return recommended_questions

def calculate_time_weights(log_data):
    """시간 기반 가중치 계산 (최근 기록에 더 높은 가중치)"""
    if not log_data:
        return {}
    
    # 가장 최근 기록의 시간
    latest_time = log_data[-1].created_at
    
    # 시간 가중치 계산 (지수 감소 함수)
    time_weights = {}
    for i, log in enumerate(log_data):
        # 시간 차이 (시간 단위)
        time_diff = (latest_time - log.created_at).total_seconds() / 3600
        
        # 지수 감소 함수: w = e^(-λt), λ는 감소율
        lambda_param = 0.1
        weight = np.exp(-lambda_param * time_diff)
        
        time_weights[log.question_id] = weight
    
    return time_weights

def analyze_success_patterns(log_data, time_weights):
    """성공/실패 패턴 분석"""
    if not log_data:
        return {}
    
    # 문제 ID별 성공/실패 횟수
    success_patterns = defaultdict(lambda: {"correct": 0, "total": 0, "weighted_correct": 0, "weighted_total": 0})
    
    for log in log_data:
        qid = log.question_id
        weight = time_weights.get(qid, 1.0)
        
        success_patterns[qid]["total"] += 1
        success_patterns[qid]["weighted_total"] += weight
        
        if log.correct:
            success_patterns[qid]["correct"] += 1
            success_patterns[qid]["weighted_correct"] += weight
    
    return success_patterns

def analyze_topic_success_rate(log_data, question_topic, time_weights):
    """주제별 성공률 분석"""
    if not log_data:
        return {1: 0.5, 2: 0.5, 3: 0.5}
    
    # 주제별 성공/실패 횟수
    topic_stats = defaultdict(lambda: {"correct": 0, "total": 0, "weighted_correct": 0, "weighted_total": 0})
    
    for log in log_data:
        qid = log.question_id
        topic = question_topic.get(qid, 1)
        weight = time_weights.get(qid, 1.0)
        
        topic_stats[topic]["total"] += 1
        topic_stats[topic]["weighted_total"] += weight
        
        if log.correct:
            topic_stats[topic]["correct"] += 1
            topic_stats[topic]["weighted_correct"] += weight
    
    # 주제별 가중 성공률 계산
    topic_success_rate = {}
    for topic, stats in topic_stats.items():
        if stats["weighted_total"] > 0:
            topic_success_rate[topic] = stats["weighted_correct"] / stats["weighted_total"]
        else:
            topic_success_rate[topic] = 0.5
    
    return topic_success_rate

def analyze_difficulty_success_rate(log_data, question_difficulty, time_weights):
    """난이도별 성공률 분석"""
    if not log_data:
        return {1: 0.5, 2: 0.5, 3: 0.5, 4: 0.5, 5: 0.5}
    
    # 난이도별 성공/실패 횟수
    difficulty_stats = defaultdict(lambda: {"correct": 0, "total": 0, "weighted_correct": 0, "weighted_total": 0})
    
    for log in log_data:
        qid = log.question_id
        difficulty = question_difficulty.get(qid, 3)
        weight = time_weights.get(qid, 1.0)
        
        difficulty_stats[difficulty]["total"] += 1
        difficulty_stats[difficulty]["weighted_total"] += weight
        
        if log.correct:
            difficulty_stats[difficulty]["correct"] += 1
            difficulty_stats[difficulty]["weighted_correct"] += weight
    
    # 난이도별 가중 성공률 계산
    difficulty_success_rate = {}
    for difficulty, stats in difficulty_stats.items():
        if stats["weighted_total"] > 0:
            difficulty_success_rate[difficulty] = stats["weighted_correct"] / stats["weighted_total"]
        else:
            difficulty_success_rate[difficulty] = 0.5
    
    return difficulty_success_rate

def calculate_question_scores(all_questions, solved_question_ids, question_difficulty, question_topic, study_level, topic_success_rate, difficulty_success_rate, rec_type):
    """문제 점수 계산"""
    question_scores = {}
    
    for question in all_questions:
        qid = question.question_id
        
        # 이미 풀었던 문제는 낮은 점수
        if qid in solved_question_ids:
            question_scores[qid] = 0.1
            continue
        
        # 난이도와 주제 정보
        difficulty = question_difficulty.get(qid, 3)
        topic = question_topic.get(qid, 1)
        
        # 난이도 적합성 점수 (학습 수준과 난이도의 차이가 작을수록 높은 점수)
        difficulty_score = 1.0 - abs(difficulty - study_level) / 5.0
        
        # 주제 성공률 점수
        topic_score = topic_success_rate.get(topic, 0.5)
        
        # 난이도 성공률 점수
        difficulty_success_score = difficulty_success_rate.get(difficulty, 0.5)
        
        # 초기 추천과 후속 추천에 따른 가중치 조정
        if rec_type == 1:  # 초기 추천
            # 초기 추천에서는 난이도 적합성에 더 높은 가중치
            question_scores[qid] = 0.5 * difficulty_score + 0.3 * topic_score + 0.2 * difficulty_success_score
        else:  # 후속 추천
            # 후속 추천에서는 주제 성공률과 난이도 성공률에 더 높은 가중치
            question_scores[qid] = 0.3 * difficulty_score + 0.4 * topic_score + 0.3 * difficulty_success_score
    
    return question_scores

def select_top_n_questions(question_scores, n):
    """상위 N개 문제 선택"""
    # 점수 기준으로 정렬
    sorted_questions = sorted(question_scores.items(), key=lambda x: x[1], reverse=True)
    
    # 상위 N개 문제 ID 선택
    top_n_ids = [qid for qid, _ in sorted_questions[:n]]
    
    # 문제 객체 가져오기
    recommended_questions = []
    for qid in top_n_ids:
        question = next((q for q in all_questions if q.question_id == qid), None)
        if question:
            recommended_questions.append(question)
    
    return recommended_questions