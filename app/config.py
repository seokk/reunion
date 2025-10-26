import os
import yaml
from typing import List, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class APIKeyConfig(BaseModel):
    key: str
    name: str


class RateLimitConfig(BaseModel):
    requests_per_minute: int
    requests_per_second: int


class TokenLimitsConfig(BaseModel):
    max_tokens_per_request: int
    max_tokens_per_day: int


class OpenAIConfig(BaseModel):
    model: str
    temperature: float
    timeout: int


class LoggingConfig(BaseModel):
    level: str
    file_path: str
    max_file_size_mb: int
    backup_count: int
    log_request_body: bool
    max_message_length: int


class Config(BaseModel):
    api_keys: List[APIKeyConfig]
    rate_limit: RateLimitConfig
    token_limits: TokenLimitsConfig
    openai: OpenAIConfig
    logging: LoggingConfig


def load_config(config_path: str = "config.yaml") -> Config:
    """YAML 설정 파일 로드"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)
    return Config(**config_dict)


def get_openai_api_key() -> str:
    """환경변수에서 OpenAI API 키 가져오기"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return api_key


# 전역 설정 인스턴스
config = load_config()
openai_api_key = get_openai_api_key()
