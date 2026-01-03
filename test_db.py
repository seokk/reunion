import asyncio
import json
import re
from app.database import prompt_db
from app.logging_config import logger

async def test_prompt_retrieval():
    """데이터베이스에서 프롬프트를 비동기적으로 조회하고 파싱을 테스트합니다."""
    logger.info("--- 데이터베이스 조회 및 파싱 테스트를 시작합니다 ---")
    
    # 1. 테스트를 위해 DB 클라이언트를 생성합니다.
    prompt_db.create_client()

    try:
        test_prompt_name = 'REUNION_ANALYSIS_SCHEMA'
        logger.info(f"테스트 대상 프롬프트 이름: '{test_prompt_name}'")

        # 2. 비동기 함수로 프롬프트 내용을 가져옵니다.
        content = await prompt_db.get_active_prompt_by_name(test_prompt_name)

        if not content:
            logger.warning(">>> 조회 실패: 활성화된 프롬프트를 찾을 수 없습니다.")
            return

        logger.info(">>> 조회 성공: 프롬프트 내용을 성공적으로 가져왔습니다.")
        
        # 3. 가져온 내용에서 주석을 제거합니다.
        # JSON은 주석을 허용하지 않으므로, '#'으로 시작하는 줄을 모두 제거합니다.
        cleaned_schema_str = re.sub(r"^\s*#.*$", "", content, flags=re.MULTILINE)
        
        # 디버깅을 위해 주석 제거 후의 문자열을 출력합니다.
        logger.info("--- 주석 제거 후 스키마 내용 ---")
        logger.info(cleaned_schema_str)
        logger.info("---------------------------------")

        # 4. 주석이 제거된 문자열을 JSON으로 파싱합니다.
        try:
            analysis_schema = json.loads(cleaned_schema_str)
            logger.info(">>> 파싱 성공: 스키마가 올바른 JSON 형식입니다.")
            # 파싱된 객체의 일부를 로깅하여 확인
            logger.info(f"파싱된 스키마 타입: {type(analysis_schema)}")
            if isinstance(analysis_schema, dict):
                logger.info(f"스키마 최상위 키: {list(analysis_schema.keys())}")

        except json.JSONDecodeError as e:
            logger.error(f">>> 파싱 실패: JSON 형식이 올바르지 않습니다. Error: {e}")
            logger.error("데이터베이스에 저장된 값이 유효한 JSON인지, 주석이 올바르게 제거되었는지 확인하세요.")
            # 실패한 문자열을 다시 로깅
            logger.error(f"파싱 실패한 문자열:\n{cleaned_schema_str}")


    except Exception as e:
        logger.error(f"테스트 중 예외 발생: {e}", exc_info=True)

    finally:
        # 5. 테스트가 끝나면 DB 클라이언트를 닫습니다.
        await prompt_db.close_client()
        logger.info("--- 데이터베이스 조회 및 파싱 테스트가 종료되었습니다 ---")


if __name__ == "__main__":
    asyncio.run(test_prompt_retrieval())
