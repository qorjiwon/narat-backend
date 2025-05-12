from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional

class NaratException(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str,
        data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.data = data

async def narat_exception_handler(request: Request, exc: NaratException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                "data": exc.data
            }
        }
    )

# 자주 사용되는 에러 정의
class QuestionNotFoundError(NaratException):
    def __init__(self, question_id: int):
        super().__init__(
            status_code=404,
            detail=f"Question with id {question_id} not found",
            error_code="QUESTION_NOT_FOUND"
        )

class CategoryNotFoundError(NaratException):
    def __init__(self, category_id: int):
        super().__init__(
            status_code=404,
            detail=f"Category with id {category_id} not found",
            error_code="CATEGORY_NOT_FOUND"
        )

class InvalidDifficultyLevelError(NaratException):
    def __init__(self, level: int):
        super().__init__(
            status_code=400,
            detail=f"Invalid difficulty level: {level}",
            error_code="INVALID_DIFFICULTY_LEVEL"
        ) 