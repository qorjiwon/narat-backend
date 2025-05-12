from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Request
from typing import Callable
import time

# 메트릭 정의
REQUEST_COUNT = Counter(
    'narat_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'narat_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

QUESTION_VIEWS = Counter(
    'narat_question_views_total',
    'Total number of question views',
    ['question_id']
)

RECOMMENDATION_REQUESTS = Counter(
    'narat_recommendation_requests_total',
    'Total number of recommendation requests',
    ['user_id']
)

async def metrics_middleware(request: Request, call_next: Callable):
    start_time = time.time()
    
    # 요청 처리
    response = await call_next(request)
    
    # 처리 시간 계산
    duration = time.time() - start_time
    
    # 메트릭 기록
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

def record_question_view(question_id: int):
    """문제 조회 메트릭 기록"""
    QUESTION_VIEWS.labels(question_id=str(question_id)).inc()

def record_recommendation_request(user_id: str):
    """추천 요청 메트릭 기록"""
    RECOMMENDATION_REQUESTS.labels(user_id=user_id).inc() 