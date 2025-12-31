import asyncio
import libsql_client
from typing import Optional
from app.config import config
from app.logging_config import logger

class PromptDB:
    """Turso DB와 상호작용하여 프롬프트를 관리하는 클래스"""
    _instance = None
    _client: Optional[libsql_client.Client] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PromptDB, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def get_client(self) -> Optional[libsql_client.Client]:
        """현재 클라이언트 인스턴스를 반환합니다."""
        return self._client

    def create_client(self):
        """데이터베이스 클라이언트를 생성하고 연결합니다."""
        if self._client is not None:
            logger.warning("DB client already exists. Skipping creation.")
            return
        try:
            self._client = libsql_client.create_client(
                url=config.turso.db_url,
                auth_token=config.turso.auth_token
            )
            logger.info("Successfully created and connected to Turso DB.")
        except Exception as e:
            logger.error(f"Failed to connect to Turso DB: {e}", exc_info=True)
            self._client = None

    async def close_client(self):
        """데이터베이스 클라이언트를 비동기적으로 닫습니다."""
        if self._client:
            try:
                await self._client.close()
                self._client = None
                logger.info("Successfully closed Turso DB connection.")
            except Exception as e:
                logger.error(f"Error closing Turso DB connection: {e}", exc_info=True)

    async def get_active_prompt_by_name(self, name: str) -> Optional[str]:
        """
        활성화된 프롬프트의 내용을 이름으로 조회합니다.
        `client.execute`는 코루틴이므로, 반드시 `await`와 함께 호출해야 합니다.
        """
        client = self.get_client()
        if not client:
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
            # 비동기 메서드를 올바르게 await 합니다.
            result = await client.execute(query, {"name": name})

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
