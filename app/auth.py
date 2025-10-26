from fastapi import Header, HTTPException, status
from app.config import config
from app.logging_config import logger, mask_api_key


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """
    API Key 인증 검증

    Args:
        x_api_key: 요청 헤더의 X-API-Key 값

    Returns:
        검증된 API Key

    Raises:
        HTTPException: 인증 실패 시 401 Unauthorized
    """
    valid_keys = [key.key for key in config.api_keys]

    if x_api_key not in valid_keys:
        logger.warning(f"Invalid API key attempt: {mask_api_key(x_api_key)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    logger.info(f"API key authenticated: {mask_api_key(x_api_key)}")
    return x_api_key


def get_api_key_name(api_key: str) -> str:
    """API Key에 해당하는 사용자 이름 반환"""
    for key_config in config.api_keys:
        if key_config.key == api_key:
            return key_config.name
    return "Unknown"
