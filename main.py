from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from responser import route_auth, route_questions, route_recommendations, route_states, route_study, route_categories
from pydantic import BaseModel
from database import engine
import models
import uvicorn
import os
from responser.logger import log_request_middleware
from responser.metrics import metrics_middleware
from responser.error_handler import narat_exception_handler, NaratException

models.Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="Narat API",
    description="Narat - 영어 문법 학습을 위한 API 서버",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS 설정
origins = os.getenv("ALLOWED_ORIGINS", "https://khuda-ml.store,https://www.khuda-ml.store").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 미들웨어 추가
app.middleware("http")(log_request_middleware)
app.middleware("http")(metrics_middleware)

# 에러 핸들러 등록
app.add_exception_handler(NaratException, narat_exception_handler)

app.include_router(route_auth.router)
app.include_router(route_questions.router)
app.include_router(route_study.router)
app.include_router(route_recommendations.router)
app.include_router(route_states.router)
app.include_router(route_categories.router)

@app.get("/")
async def read_root():
    return {"success": True}

@app.get("/get")
async def read_get(q: str):
    return JSONResponse({"success": q})

class TestPostItem(BaseModel):
    item: str
@app.post("/post")
async def read_post(item: TestPostItem):
    return JSONResponse({"success": item.item})

if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)