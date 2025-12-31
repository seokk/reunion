from openai import OpenAI, OpenAIError
from fastapi import HTTPException, status
from typing import AsyncGenerator, Dict, Any
import asyncio
import json
import re # 정규표현식 모듈 추가
from app.config import config, openai_api_key
from app.logging_config import logger, truncate_message
from app.database import prompt_db

class LLMService:
    """OpenAI API 호출 서비스"""

    def __init__(self):
        self.client = OpenAI(api_key=openai_api_key)
        self.system_prompt: str = ""
        self.analysis_schema: Dict[str, Any] = {}

    async def _load_prompts_from_db(self):
        """DB에서 활성화된 시스템 프롬프트와 JSON 스키마를 비동기적으로 로드합니다."""
        logger.info("Attempting to load prompts and schemas from database asynchronously...")
        
        system_prompt_content = await prompt_db.get_active_prompt_by_name('REUNION_CONSULTATION_SYSTEM_PROMPT')
        if not system_prompt_content:
            logger.error("Fatal: Could not load active system prompt from DB.")
            raise ValueError("Failed to load required system prompt from the database.")
        self.system_prompt = system_prompt_content

        analysis_schema_str = await prompt_db.get_active_prompt_by_name('REUNION_ANALYSIS_SCHEMA')
        if not analysis_schema_str:
            logger.error("Fatal: Could not load active analysis schema from DB.")
            raise ValueError("Failed to load required analysis schema from the database.")
        
        try:
            # 1. DB에서 읽어온 문자열에서 주석을 제거합니다.
            # 각 줄의 시작 부분에 있는 # 주석을 제거합니다.
            cleaned_schema_str = re.sub(r"^\s*#.*$", "", analysis_schema_str, flags=re.MULTILINE)
            
            # 2. 주석이 제거된 문자열을 JSON으로 파싱합니다.
            self.analysis_schema = json.loads(cleaned_schema_str)
            logger.info("Successfully loaded and parsed all required prompts and schemas.")

        except json.JSONDecodeError as e:
            logger.error(f"Fatal: Failed to parse analysis schema from DB. Error: {e}")
            logger.debug(f"Cleaned schema string that failed to parse: {cleaned_schema_str}")
            raise ValueError("Invalid JSON format in the analysis schema from the database.")

    async def chat_completion(self, message: str, max_tokens: int = None, use_structured_output: bool = True) -> tuple[str, int]:
        """
        일반 채팅 완성 (한 번에 전체 응답)
        """
        if max_tokens is None:
            max_tokens = config.token_limits.max_tokens_per_request

        try:
            logger.info(f"Requesting chat completion - Message: {truncate_message(message)}, Max tokens: {max_tokens}, Structured: {use_structured_output}")

            api_params = {
                "model": config.openai.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": message}
                ],
                "max_tokens": max_tokens,
                "temperature": config.openai.temperature
            }

            if use_structured_output:
                api_params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "reunion_analysis",
                        "schema": self.analysis_schema,
                        "strict": True
                    }
                }

            response = await asyncio.to_thread(
                self.client.chat.completions.create, **api_params
            )

            response_text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            if use_structured_output:
                try:
                    json.loads(response_text)
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
        """
        if max_tokens is None:
            max_tokens = config.token_limits.max_tokens_per_request

        try:
            logger.info(f"Requesting streaming chat completion - Message: {truncate_message(message)}, Max tokens: {max_tokens}")

            stream = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=config.openai.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
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

                if chunk.choices[0].finish_reason is not None:
                    if hasattr(chunk, 'usage') and chunk.usage:
                        total_tokens = chunk.usage.total_tokens

            logger.info(
                f"Streaming completion successful - "
                f"Chunks sent: {chunk_count}, Estimated tokens: {total_tokens}"
            )

            yield "", True, total_tokens

        except OpenAIError as e:
            logger.error(f"OpenAI API streaming error: {str(e)}")
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


# --- 의존성 주입을 위한 새로운 설정 ---

_llm_service_instance = None
_llm_service_lock = asyncio.Lock()

async def get_llm_service() -> LLMService:
    """
    FastAPI 의존성 주입을 통해 LLMService의 싱글턴 인스턴스를 관리합니다.
    필요한 경우, 비동기적으로 프롬프트를 로드하여 인스턴스를 초기화합니다.
    """
    global _llm_service_instance
    if _llm_service_instance is None:
        async with _llm_service_lock:
            if _llm_service_instance is None:
                _llm_service_instance = LLMService()
                await _llm_service_instance._load_prompts_from_db()
    return _llm_service_instance
