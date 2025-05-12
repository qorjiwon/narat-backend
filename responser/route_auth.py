from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import datetime
import models
from dbmanage import get_db
from sqlalchemy.orm import Session
from google.auth.transport import requests
from google.oauth2 import id_token
from uuid import uuid4
import os
from dotenv import load_dotenv

header = "/api/auth"
router = APIRouter(
    prefix = header,
    tags   = ['auth']
)
load_dotenv()
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')

@router.get('/')
async def root():
    return {"success": "true"}

class GoogleLogin(BaseModel):
    credential: str
    email: str
    name: str
    picture: str

@router.post('/google')
async def google_login(item: GoogleLogin, db: Session = Depends(get_db)):
    try:
        # 받은 토큰 검증
        id_info = id_token.verify_oauth2_token(item.credential, requests.Request(), GOOGLE_CLIENT_ID)

        # 이메일과 이름 추출
        email = id_info.get("email")
        name = id_info.get("name")

        if not email or not name:
            raise HTTPException(status_code=400, detail="Invalid token payload")

        # 사용자 조회 또는 생성
        user = db.query(models.UserDB).filter(models.UserDB.email == email).first()
        if user is None:
            user = models.UserDB(
                google_id=str(uuid4()),
                email=email,
                display_name=name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.last_login = datetime.datetime.now()
            db.commit()

        # 세션 생성
        session = models.SessionDB(
            session_id=str(uuid4()),
            google_id=user.google_id
        )
        db.add(session)
        db.commit()

        return JSONResponse({
            "token": session.session_id,
            "display_name": user.display_name,
            "study_level": user.study_level
        })
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token")

class Verify(BaseModel):
    session_token: str

@router.post('/verify')
async def verify_session(item: Verify, db: Session = Depends(get_db)):
    session = db.query(models.SessionDB).filter(models.SessionDB.session_id == item.session_token).first()
    if session is None:
        raise HTTPException(status_code=400, detail="Invalid session token")
    
    return JSONResponse({
        "is_valid": True,
        "display_name": session.session_owner.display_name,
        "study_level": session.session_owner.study_level
    })

@router.post('/logout')
async def logout(item: Verify, db: Session = Depends(get_db)):
    session = db.query(models.SessionDB).filter(models.SessionDB.session_id == item.session_token).first()
    if session is None:
        raise HTTPException(status_code=400, detail="Invalid session token")
    
    db.delete(session)
    db.commit()
    return JSONResponse({
        "success": True
    })

@router.post('/test_session_create')
async def test_session_create(item: GoogleLogin, db: Session = Depends(get_db)):
    if os.environ.get('TEST_SESSION_TOKEN') != item.credential:
        raise HTTPException(status_code=400, detail="Invalid environment")
    data = db.query(models.UserDB).filter(models.UserDB.email == "test@test.com").first()
    if data is not None:
        session = models.SessionDB(session_id=str(uuid4()), google_id=data.google_id)
        db.add(session)
        db.commit()
        return JSONResponse({
            "session_token": session.session_id,
            "display_name": data.display_name,
            "study_level" : data.study_level
        })
    else:
        raise HTTPException(status_code=400, detail="User not found")