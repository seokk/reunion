from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from app.models import ChatRequest, ChatResponse, ErrorResponse
from app.auth import verify_api_key, get_api_key_name
from app.rate_limiter import rate_limiter
from app.llm_service import llm_service
from app.logging_config import logger, mask_api_key, truncate_message
from app.config import config
import json
import uvicorn
import os

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="LLM Service API",
    description="FastAPI 기반 ChatGPT 서비스",
    version="1.0.0"
)

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 오리진 허용 (프로덕션에서는 특정 도메인만 허용 권장)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)


@app.get("/")
async def root():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "service": "LLM Service API"}


@app.post(
    "/api/v1/chat/",
    response_model=ChatResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Token limit exceeded"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    일반 채팅 엔드포인트 (전체 응답 한 번에 반환)

    Args:
        request: FastAPI Request
        chat_request: 채팅 요청 데이터
        api_key: 인증된 API Key

    Returns:
        ChatResponse: ChatGPT 응답 및 토큰 정보
    """
    start_time = datetime.now()
    user_name = get_api_key_name(api_key)

    try:
        # Rate Limit 체크
        rate_limiter.check_rate_limit(api_key, request)

        # 요청할 토큰 수 결정
        max_tokens = chat_request.max_tokens or config.token_limits.max_tokens_per_request

        # 토큰 제한 체크
        rate_limiter.check_token_limit(api_key, max_tokens)
        
        log_message = json.dumps(
            truncate_message(chat_request.message),
            ensure_ascii=False
        )

        logger.info(
            f"Chat request - User: {user_name}, API Key: {mask_api_key(api_key)}, "
            f"IP: {request.client.host if request.client else 'unknown'}, "
            f"Message: {log_message}"
        )

        # LLM 호출
        response_text, tokens_used = await llm_service.chat_completion(
            message=chat_request.message,
            max_tokens=max_tokens
        )

        # 토큰 사용량 업데이트
        tokens_remaining = rate_limiter.add_token_usage(api_key, tokens_used)

        # 응답 시간 계산
        elapsed_time = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"Chat response - User: {user_name}, API Key: {mask_api_key(api_key)}, "
            f"Tokens used: {tokens_used}, Remaining: {tokens_remaining}, "
            f"Response time: {elapsed_time:.2f}s"
        )

        return ChatResponse(
            response=response_text,
            tokens_used=tokens_used,
            tokens_remaining_today=tokens_remaining
        )

    except HTTPException:
        # 이미 처리된 HTTP 예외는 다시 발생
        raise

    except Exception as e:
        logger.error(
            f"Unexpected error in chat endpoint - User: {user_name}, "
            f"API Key: {mask_api_key(api_key)}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post(
    "/api/v1/chat/stream/",
    responses={
        200: {"description": "Server-Sent Events stream"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Token limit exceeded"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    스트리밍 채팅 엔드포인트 (실시간 응답)

    Args:
        request: FastAPI Request
        chat_request: 채팅 요청 데이터
        api_key: 인증된 API Key

    Returns:
        StreamingResponse: Server-Sent Events 스트림
    """
    start_time = datetime.now()
    user_name = get_api_key_name(api_key)

    try:
        # Rate Limit 체크
        rate_limiter.check_rate_limit(api_key, request)

        # 요청할 토큰 수 결정
        max_tokens = chat_request.max_tokens or config.token_limits.max_tokens_per_request

        # 토큰 제한 체크
        rate_limiter.check_token_limit(api_key, max_tokens)

        log_message = json.dumps(
            truncate_message(chat_request.message),
            ensure_ascii=False
        )

        logger.info(
            f"Chat request - User: {user_name}, API Key: {mask_api_key(api_key)}, "
            f"IP: {request.client.host if request.client else 'unknown'}, "
            f"Message: {log_message}"
        )

        async def generate_stream():
            """SSE 스트림 생성"""
            try:
                total_tokens = 0
                async for chunk, done, tokens in llm_service.chat_completion_stream(
                    message=chat_request.message,
                    max_tokens=max_tokens
                ):
                    if done:
                        # 스트림 완료
                        total_tokens = tokens
                        # 토큰 사용량 업데이트
                        tokens_remaining = rate_limiter.add_token_usage(api_key, total_tokens)

                        # 완료 메시지
                        data = {
                            "chunk": "",
                            "done": True,
                            "tokens_used": total_tokens,
                            "tokens_remaining_today": tokens_remaining
                        }
                        yield f"data: {json.dumps(data)}\n\n"

                        # 로그 기록
                        elapsed_time = (datetime.now() - start_time).total_seconds()
                        logger.info(
                            f"Stream completed - User: {user_name}, API Key: {mask_api_key(api_key)}, "
                            f"Tokens used: {total_tokens}, Remaining: {tokens_remaining}, "
                            f"Response time: {elapsed_time:.2f}s"
                        )
                    else:
                        # 청크 전송
                        data = {
                            "chunk": chunk,
                            "done": False
                        }
                        yield f"data: {json.dumps(data)}\n\n"

            except Exception as e:
                logger.error(
                    f"Error during streaming - User: {user_name}, "
                    f"API Key: {mask_api_key(api_key)}, Error: {str(e)}"
                )
                error_data = {
                    "error": str(e),
                    "done": True
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream"
        )

    except HTTPException:
        # 이미 처리된 HTTP 예외는 다시 발생
        raise

    except Exception as e:
        logger.error(
            f"Unexpected error in stream endpoint - User: {user_name}, "
            f"API Key: {mask_api_key(api_key)}, Error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 핸들러"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    # docker-compose.yml에서 사용하는 포트와 일치시키기 위해 기본 포트를 8080으로 변경
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    # Cloud Run과 같은 역방향 프록시 뒤에서 실행할 때 필요
    uvicorn.run(app, host=host, port=port, proxy_headers=True)
