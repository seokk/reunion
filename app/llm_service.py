from openai import OpenAI, OpenAIError
from fastapi import HTTPException, status
from typing import AsyncGenerator
import asyncio
import json
from app.config import config, openai_api_key
from app.logging_config import logger, truncate_message
from app.prompts import REUNION_CONSULTATION_SYSTEM_PROMPT
from app.schemas import REUNION_ANALYSIS_SCHEMA


class LLMService:
    """OpenAI API 호출 서비스"""

    def __init__(self):
        self.client = OpenAI(
            api_key=openai_api_key
        )

    async def chat_completion(self, message: str, max_tokens: int = None, use_structured_output: bool = True) -> tuple[str, int]:
        """
        일반 채팅 완성 (한 번에 전체 응답)

        Args:
            message: 사용자 질의
            max_tokens: 최대 토큰 수 (None이면 config 기본값 사용)
            use_structured_output: Structured Output 사용 여부 (기본 True)

        Returns:
            tuple[응답 텍스트 (JSON 문자열 or 일반 텍스트), 사용된 토큰 수]

        Raises:
            HTTPException: OpenAI API 에러 시
        """
        if max_tokens is None:
            max_tokens = config.token_limits.max_tokens_per_request

        try:
            logger.info(f"Requesting chat completion - Message: {truncate_message(message)}, Max tokens: {max_tokens}, Structured: {use_structured_output}")

            # API 호출 파라미터 구성
            api_params = {
                "model": config.openai.model,
                "messages": [
                    {"role": "system", "content": REUNION_CONSULTATION_SYSTEM_PROMPT},
                    {"role": "user", "content": message}
                ],
                "max_tokens": max_tokens,
                "temperature": config.openai.temperature
            }

            # Structured Output 사용 시 response_format 추가
            if use_structured_output:
                api_params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "reunion_analysis",
                        "schema": REUNION_ANALYSIS_SCHEMA,
                        "strict": True
                    }
                }

            # OpenAI API 호출 (동기)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(**api_params)
            )

            # 응답 추출
            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            # Structured Output인 경우 JSON 유효성 검증
            if use_structured_output:
                try:
                    json.loads(response_text)  # JSON 파싱 테스트
                    logger.info(f"Structured output validated successfully")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in structured output: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Invalid JSON structure in LLM response"
                    )

            logger.info(
                f"Chat completion successful - "
                f"Response length: {len(response_text)}, Tokens used: {tokens_used}"
            )

            return response_text, tokens_used

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            if "rate_limit" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="OpenAI API rate limit exceeded. Please try again later."
                )
            elif "invalid" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid request: {str(e)}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"OpenAI API error: {str(e)}"
                )

        except Exception as e:
            logger.error(f"Unexpected error during chat completion: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}"
            )

    async def chat_completion_stream(self, message: str, max_tokens: int = None) -> AsyncGenerator[tuple[str, bool, int], None]:
        """
        스트리밍 채팅 완성

        Args:
            message: 사용자 질의
            max_tokens: 최대 토큰 수

        Yields:
            tuple[청크 텍스트, 완료 여부, 사용된 토큰 수]

        Raises:
            HTTPException: OpenAI API 에러 시
        """
        if max_tokens is None:
            max_tokens = config.token_limits.max_tokens_per_request

        try:
            logger.info(f"Requesting streaming chat completion - Message: {truncate_message(message)}, Max tokens: {max_tokens}")

            # OpenAI API 스트리밍 호출
            stream = self.client.chat.completions.create(
                model=config.openai.model,
                messages=[
                    {"role": "system", "content": REUNION_CONSULTATION_SYSTEM_PROMPT},
                    {"role": "user", "content": message}
                ],
                max_tokens=max_tokens,
                temperature=config.openai.temperature,
                stream=True
            )

            total_tokens = 0
            chunk_count = 0

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    chunk_count += 1
                    yield content, False, 0

                # 스트림 완료
                if chunk.choices[0].finish_reason is not None:
                    # OpenAI 스트리밍에서는 usage 정보가 마지막에 제공되지 않을 수 있음
                    # 대략적인 토큰 수 계산 (실제로는 별도 API 호출 필요)
                    # 여기서는 간단히 추정값 사용
                    total_tokens = chunk.usage.total_tokens if hasattr(chunk, 'usage') and chunk.usage else 0

            logger.info(
                f"Streaming completion successful - "
                f"Chunks sent: {chunk_count}, Estimated tokens: {total_tokens}"
            )

            # 완료 신호
            yield "", True, total_tokens

        except OpenAIError as e:
            logger.error(f"OpenAI API streaming error: {str(e)}")
            if "rate_limit" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="OpenAI API rate limit exceeded. Please try again later."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"OpenAI API error: {str(e)}"
                )

        except Exception as e:
            logger.error(f"Unexpected error during streaming: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}"
            )


# 전역 LLM 서비스 인스턴스
llm_service = LLMService()
