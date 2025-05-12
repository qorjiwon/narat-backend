from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import datetime
import models
from dbmanage import get_db
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo
from uuid import uuid4
import os
from dotenv import load_dotenv

header = "/api/states"
router = APIRouter(
    prefix = header,
    tags   = ['states']
)
KST = ZoneInfo("Asia/Seoul")

@router.get('/')
async def root():
    return {"success": "true"}

class StateUserForm(BaseModel):
    session_token: str

@router.post('/user')
async def user(item: StateUserForm, db: Session = Depends(get_db)):
    data_session = db.query(models.SessionDB).filter(models.SessionDB.session_token == item.session_token).first()
    if data_session is None:
        raise HTTPException(status_code=403, detail="User not found")   

    data = db.query(models.UserLogDB).filter(models.UserLogDB.google_id == data_session.google_id).all()
    log_data_result = []
    for row in data:
        log_data_result.append({
            "item": {
                "question_id": row.question_id,
                "rating":  (0 if row.correct else 1),
                "timestamp": row.timestamp.replace(tzinfo=datetime.timezone.utc).astimezone(tz=KST).surftime("%Y-%m-%d %H:%M:%S")
            }
        })
    
    return JSONResponse({"study_states": log_data_result})

@router.get('/questions/{question_id}')
async def questions(question_id: int, db: Session = Depends(get_db)):
    data = db.query(models.UserLogDB).filter(models.UserLogDB.question_id == question_id).all()
    log_data_result = []
    for row in data:
        log_data_result.append({
            "item": {
                "rating":  (0 if row.correct else 1),
                "timestamp": row.timestamp.replace(tzinfo=datetime.timezone.utc).astimezone(tz=KST).surftime("%Y-%m-%d %H:%M:%S")
            }
        })
    
    return JSONResponse({"question_states": log_data_result})