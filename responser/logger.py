import logging
import time
from fastapi import Request
from typing import Callable
import json

# 로거 설정
logger = logging.getLogger("narat")
logger.setLevel(logging.INFO)

# 파일 핸들러
file_handler = logging.FileHandler("narat.log")
file_handler.setLevel(logging.INFO)

# 포맷터
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
file_handler.setFormatter(formatter)

# 핸들러 추가
logger.addHandler(file_handler)

async def log_request_middleware(request: Request, call_next: Callable):
    # 요청 시작 시간
    start_time = time.time()
    
    # 요청 정보 로깅
    logger.info(f"Request: {request.method} {request.url}")
    if request.headers.get("content-type") == "application/json":
        try:
            body = await request.json()
            logger.info(f"Request body: {json.dumps(body)}")
        except:
            pass
    
    # 응답 처리
    response = await call_next(request)
    
    # 처리 시간 계산
    process_time = time.time() - start_time
    
    # 응답 정보 로깅
    logger.info(
        f"Response: {request.method} {request.url} - "
        f"Status: {response.status_code} - "
        f"Process Time: {process_time:.2f}s"
    )
    
    return response

def log_error(error: Exception, context: dict = None):
    """에러 로깅 헬퍼 함수"""
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {}
    }
    logger.error(json.dumps(error_data)) 