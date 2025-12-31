import libsql_client
import json
from typing import Optional, List
from app.config import config
from app.logging_config import logger

class PromptDB:
    """Turso DB와 상호작용하여 프롬프트를 관리하는 클래스"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PromptDB, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'client'): # 중복 초기화 방지
            try:
                self.client = libsql_client.create_client(
                    url=config.turso.db_url,
                    auth_token=config.turso.auth_token
                )
                logger.info("Successfully connected to Turso DB.")
            except Exception as e:
                logger.error(f"Failed to connect to Turso DB: {e}", exc_info=True)
                self.client = None

    def get_active_prompt_by_name(self, name: str) -> Optional[str]:
        """
        활성화된 프롬프트의 내용을 이름으로 조회합니다.

        Args:
            name: prompt_types 테이블의 프롬프트 이름

        Returns:
            활성화된 프롬프트의 content 문자열, 없으면 None
        """
        if not self.client:
            logger.error("Cannot get prompt, DB client is not available.")
            return None

        query = """
            SELECT pv.content
            FROM prompt_versions pv
            JOIN prompt_types pt ON pv.prompt_type_id = pt.id
            WHERE pt.name = :name AND pv.is_active = 1
            ORDER BY pv.version DESC
            LIMIT 1;
        """
        try:
            logger.debug(f"Executing query to get active prompt: {name}")
            result = self.client.execute(query, {"name": name})
            
            if result.rows:
                content = result.rows[0]["content"]
                logger.info(f"Successfully loaded active prompt for '{name}'.")
                return content
            else:
                logger.warning(f"No active prompt found for name: {name}")
                return None
        except Exception as e:
            logger.error(f"Error fetching prompt '{name}' from DB: {e}", exc_info=True)
            return None

# 애플리케이션 전체에서 사용할 DB 인스턴스 생성
prompt_db = PromptDB()
