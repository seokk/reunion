
import asyncio
import os
import libsql_client
import sys

async def run_diagnostic():
    """DB 연결을 진단하는 최소 기능의 스크립트"""
    
    # --- 1. 환경 변수에서 URL과 토큰을 가져옵니다 ---
    db_url = os.getenv("TURSO_DATABASE_URL")
    auth_token = os.getenv("TURSO_AUTH_TOKEN")

    if not db_url or not auth_token:
        print("오류: TURSO_DATABASE_URL와 TURSO_AUTH_TOKEN 환경 변수를 설정해야 합니다.", file=sys.stderr)
        sys.exit(1)

    print(f"진단 시작: {db_url} 에 연결을 시도합니다...")
    
    client = None
    try:
        # --- 2. 클라이언트 생성을 시도합니다 ---
        client = libsql_client.create_client(url=db_url, auth_token=auth_token)
        print("클라이언트 생성 성공. 서버에 간단한 쿼리를 전송합니다...")

        # --- 3. 가장 간단한 쿼리를 실행하여 실제 통신을 확인합니다 ---
        result = await client.execute("SELECT 1")
        print("쿼리 성공! 서버로부터 응답을 받았습니다.")
        print(f"응답 내용: {result.rows}")

    except Exception as e:
        print("\n--- 연결 또는 쿼리 실패 ---", file=sys.stderr)
        print(f"오류 유형: {type(e).__name__}", file=sys.stderr)
        print(f"오류 내용: {e}", file=sys.stderr)
        print("--------------------------", file=sys.stderr)
        print("\n진단 실패: 데이터베이스에 연결할 수 없습니다. URL, 인증 토큰, 네트워크 방화벽 설정을 확인해주세요.", file=sys.stderr)

    finally:
        # --- 4. 클라이언트를 종료합니다 ---
        if client:
            await client.close()
            print("연결을 성공적으로 종료했습니다.")

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
