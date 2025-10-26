from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    message: str = Field(..., description="사용자 질의 메시지")
    max_tokens: Optional[int] = Field(None, description="최대 토큰 수 (선택적)")


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str = Field(..., description="ChatGPT 응답")
    tokens_used: int = Field(..., description="사용된 토큰 수")
    tokens_remaining_today: int = Field(..., description="오늘 남은 토큰 수")


class StreamChunk(BaseModel):
    """스트리밍 청크 모델"""
    chunk: str = Field(..., description="응답 청크")
    done: bool = Field(..., description="스트림 완료 여부")
    tokens_used: Optional[int] = Field(None, description="사용된 토큰 수 (완료시)")


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 에러 정보")
