import asyncio
from app.database import prompt_db
from app.logging_config import logger

async def test_prompt_retrieval():
    """데이터베이스에서 프롬프트를 비동기적으로 조회하여 테스트합니다."""
    logger.info("--- 데이터베이스 조회 테스트를 시작합니다 ---")
    
    # 1. 테스트를 위해 DB 클라이언트를 직접 생성합니다.
    prompt_db.create_client()

    try:
        test_prompt_name = 'REUNION_CONSULTATION_SYSTEM_PROMPT'
        test_prompt_name2 = 'REUNION_ANALYSIS_SCHEMA'
        logger.info(f"테스트 대상 프롬프트 이름: '{test_prompt_name2}'")

        # 비동기 함수 호출
        content = await prompt_db.get_active_prompt_by_name(test_prompt_name2)

        if content:
            logger.info(f">>> 조회 성공: 프롬프트 내용을 성공적으로 가져왔습니다.")
            logger.info(f"content: {content}")
        else:
            logger.warning(f">>> 조회 실패: 활성화된 프롬프트를 찾을 수 없습니다 (결과는 None입니다).")
            logger.warning("확인 사항: 'prompt_types' 테이블에 해당 이름의 데이터가 있고, ")
            logger.warning("그에 연결된 'prompt_versions' 테이블의 데이터의 'is_active' 필드가 1로 설정되어 있는지 확인해주세요.")

    finally:
        # 2. 테스트가 끝나면 DB 클라이언트를 닫습니다.
        await prompt_db.close_client()
        logger.info("--- 데이터베이스 조회 테스트가 종료되었습니다 ---")

if __name__ == "__main__":
    # 비동기 함수 실행
    asyncio.run(test_prompt_retrieval())
