from fastapi import HTTPException, status, Request
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, Deque
from app.config import config
from app.logging_config import logger, mask_api_key


class RateLimiter:
    """메모리 기반 Rate Limiter"""

    def __init__(self):
        # API Key별 요청 시간 기록 (분 단위)
        self.minute_requests: Dict[str, Deque[datetime]] = defaultdict(deque)
        # API Key별 요청 시간 기록 (초 단위)
        self.second_requests: Dict[str, Deque[datetime]] = defaultdict(deque)
        # API Key별 일일 토큰 사용량
        self.daily_tokens: Dict[str, Dict[str, int]] = defaultdict(lambda: {"date": datetime.now().date(), "tokens": 0})

    def _clean_old_requests(self, api_key: str):
        """오래된 요청 기록 제거"""
        now = datetime.now()

        # 1분 이상 지난 요청 제거
        while self.minute_requests[api_key] and (now - self.minute_requests[api_key][0]) > timedelta(minutes=1):
            self.minute_requests[api_key].popleft()

        # 1초 이상 지난 요청 제거
        while self.second_requests[api_key] and (now - self.second_requests[api_key][0]) > timedelta(seconds=1):
            self.second_requests[api_key].popleft()

    def check_rate_limit(self, api_key: str, request: Request) -> None:
        """
        Rate Limit 검증

        Args:
            api_key: API Key
            request: FastAPI Request 객체

        Raises:
            HTTPException: Rate limit 초과 시 429 Too Many Requests
        """
        self._clean_old_requests(api_key)
        now = datetime.now()

        # 초당 요청 수 체크 (악의적 공격 방지)
        if len(self.second_requests[api_key]) >= config.rate_limit.requests_per_second:
            logger.warning(
                f"Rate limit exceeded (per second): {mask_api_key(api_key)} - "
                f"IP: {request.client.host if request.client else 'unknown'}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Maximum {config.rate_limit.requests_per_second} requests per second allowed."
            )

        # 분당 요청 수 체크
        if len(self.minute_requests[api_key]) >= config.rate_limit.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded (per minute): {mask_api_key(api_key)} - "
                f"IP: {request.client.host if request.client else 'unknown'}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Maximum {config.rate_limit.requests_per_minute} requests per minute allowed."
            )

        # 요청 기록 추가
        self.minute_requests[api_key].append(now)
        self.second_requests[api_key].append(now)

    def get_remaining_requests(self, api_key: str) -> Dict[str, int]:
        """남은 요청 횟수 반환"""
        self._clean_old_requests(api_key)
        return {
            "remaining_per_minute": config.rate_limit.requests_per_minute - len(self.minute_requests[api_key]),
            "remaining_per_second": config.rate_limit.requests_per_second - len(self.second_requests[api_key])
        }

    def check_token_limit(self, api_key: str, requested_tokens: int) -> None:
        """
        토큰 제한 검증

        Args:
            api_key: API Key
            requested_tokens: 요청하려는 토큰 수

        Raises:
            HTTPException: 토큰 제한 초과 시 403 Forbidden
        """
        # 요청당 토큰 제한 체크
        if requested_tokens > config.token_limits.max_tokens_per_request:
            logger.warning(
                f"Token limit exceeded (per request): {mask_api_key(api_key)} - "
                f"Requested: {requested_tokens}, Max: {config.token_limits.max_tokens_per_request}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requested tokens ({requested_tokens}) exceeds maximum allowed per request ({config.token_limits.max_tokens_per_request})"
            )

        # 일일 토큰 사용량 체크
        token_info = self.daily_tokens[api_key]
        today = datetime.now().date()

        # 날짜가 바뀌면 초기화
        if token_info["date"] != today:
            token_info["date"] = today
            token_info["tokens"] = 0

        if token_info["tokens"] + requested_tokens > config.token_limits.max_tokens_per_day:
            logger.warning(
                f"Daily token limit exceeded: {mask_api_key(api_key)} - "
                f"Used: {token_info['tokens']}, Requested: {requested_tokens}, Max: {config.token_limits.max_tokens_per_day}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Daily token limit exceeded. Used: {token_info['tokens']}, Requested: {requested_tokens}, Max: {config.token_limits.max_tokens_per_day}"
            )

    def add_token_usage(self, api_key: str, tokens_used: int) -> int:
        """
        토큰 사용량 추가 및 남은 토큰 반환

        Args:
            api_key: API Key
            tokens_used: 사용된 토큰 수

        Returns:
            오늘 남은 토큰 수
        """
        token_info = self.daily_tokens[api_key]
        today = datetime.now().date()

        # 날짜가 바뀌면 초기화
        if token_info["date"] != today:
            token_info["date"] = today
            token_info["tokens"] = 0

        token_info["tokens"] += tokens_used
        remaining = config.token_limits.max_tokens_per_day - token_info["tokens"]

        logger.info(
            f"Token usage updated: {mask_api_key(api_key)} - "
            f"Used: {tokens_used}, Total today: {token_info['tokens']}, Remaining: {remaining}"
        )

        return max(0, remaining)


# 전역 Rate Limiter 인스턴스
rate_limiter = RateLimiter()
