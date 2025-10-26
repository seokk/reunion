import logging
import os
from logging.handlers import RotatingFileHandler
from app.config import config


def setup_logging():
    """로깅 설정"""
    # logs 디렉토리 생성
    log_dir = os.path.dirname(config.logging.file_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 로거 생성
    logger = logging.getLogger("llm_service")
    logger.setLevel(getattr(logging, config.logging.level))

    # 기존 핸들러 제거
    logger.handlers.clear()

    # 파일 핸들러 (로테이션)
    max_bytes = config.logging.max_file_size_mb * 1024 * 1024
    file_handler = RotatingFileHandler(
        config.logging.file_path,
        maxBytes=max_bytes,
        backupCount=config.logging.backup_count,
        encoding='utf-8'
    )

    # 포매터 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    # 콘솔 핸들러 (개발 시 편의)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 전역 로거 인스턴스
logger = setup_logging()


def mask_api_key(api_key: str) -> str:
    """API 키 마스킹 (앞 3자, 뒤 3자만 표시)"""
    if len(api_key) <= 6:
        return "***"
    return f"{api_key[:3]}***{api_key[-3:]}"


def truncate_message(message: str, max_length: int = None) -> str:
    """메시지 길이 제한"""
    if max_length is None:
        max_length = config.logging.max_message_length

    if len(message) <= max_length:
        return message
    return message[:max_length] + "..."
