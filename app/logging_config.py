import logging
import os
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
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

    # --- 파일 핸들러 (기존 포맷 유지) ---
    max_bytes = config.logging.max_file_size_mb * 1024 * 1024
    file_handler = RotatingFileHandler(
        config.logging.file_path,
        maxBytes=max_bytes,
        backupCount=config.logging.backup_count,
        encoding='utf-8'
    )
    # 파일용 텍스트 포매터
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # --- 콘솔 핸들러 (JsonFormatter 사용) ---
    console_handler = logging.StreamHandler()

    # JSON 포매터 설정
    # Cloud Run의 구조화된 로깅과 호환되도록 필드명을 맞춥니다.
    # https://cloud.google.com/run/docs/logging#structured-json
    # 포맷 문자열에 필요한 필드를 명시하고, rename_fields를 통해 이름을 변경합니다.
    formatter_string = '%(asctime)s %(levelname)s %(message)s'
    json_formatter = jsonlogger.JsonFormatter(
        formatter_string,
        rename_fields={'levelname': 'severity', 'asctime': 'timestamp'}
    )

    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    # uvicorn 액세스 로그도 동일한 포맷을 사용하도록 설정
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers = logger.handlers
    uvicorn_access_logger.setLevel(logger.level)

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
