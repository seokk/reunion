# b_reunion 프로젝트 분석 (백엔드)

## 1) 개요
- 기술 스택: `FastAPI`, `Uvicorn`, `OpenAI Python SDK`, `libsql-client(Turso)`, `Pydantic v2`
- 엔트리포인트: `main.py`
- 목적: 입력 메시지를 LLM으로 분석하고, JSON 스키마 기반 응답을 반환하는 API 서버

## 2) 디렉터리/핵심 파일
- `main.py`: API 라우트, 예외 핸들러, 앱 lifespan(시작/종료 훅)
- `app/config.py`: `config.yaml` 로드 + `OPENAI_API_KEY` 환경변수 로드
- `app/auth.py`: `X-API-Key` 인증
- `app/rate_limiter.py`: 메모리 기반 요청/토큰 제한
- `app/llm_service.py`: OpenAI 호출, DB에서 시스템 프롬프트/스키마 로드
- `app/database.py`: Turso 연결 및 활성 프롬프트 조회
- `app/logging_config.py`: 파일/콘솔(JSON) 로깅
- `config.yaml`: API 키, 레이트리밋, 토큰 제한, OpenAI/Turso 설정

## 3) 런타임 구조
1. 서버 시작 시 `lifespan`에서 `prompt_db.create_client()` 실행
2. 첫 요청 시 `get_llm_service()`가 싱글톤 `LLMService` 생성
3. `LLMService`가 Turso에서 아래 프롬프트를 로드
   - `REUNION_CONSULTATION_SYSTEM_PROMPT`
   - `REUNION_ANALYSIS_SCHEMA`
4. `/api/v1/chat/` 호출 시:
   - API 키 인증 (`X-API-Key`)
   - 요청/토큰 제한 체크
   - OpenAI `chat.completions.create()` 호출
   - `response_format=json_schema`로 구조화 출력 요청
   - 사용 토큰을 일일 카운터에 반영 후 응답
5. `/api/v1/chat/stream/`은 SSE로 청크 전송

## 4) API 명세(요약)
- `GET /`: 헬스체크
- `POST /api/v1/chat/`
  - 요청: `{ message: string, max_tokens?: number }`
  - 응답: `{ response: string, tokens_used: number, tokens_remaining_today: number }`
- `POST /api/v1/chat/stream/`
  - SSE(`text/event-stream`)로 chunk/done 이벤트 전송

## 5) 설정/배포
- 로컬 실행
  - `pip install -r requirements.txt`
  - `.env`에 `OPENAI_API_KEY` 필요
  - `python main.py` 또는 `uvicorn main:app --reload --port 8080`
- Docker
  - `Dockerfile`/`docker-compose.yml` 제공
  - compose에서 `config.yaml` read-only 마운트

## 6) 유지보수 관점 핵심 포인트
- 프롬프트/스키마가 코드가 아니라 DB(Turso)에 있어 운영 중 변경 가능
- `RateLimiter`는 프로세스 메모리 기반
  - 멀티 인스턴스/재시작 환경에서 일관성 없음
- `chat_completion_stream`의 토큰 계산은 스트림 usage 의존이라 0으로 남을 수 있음
- CORS `allow_origins=["*"]`로 전면 허용 상태
- 예외 응답에서 내부 에러 문자열을 클라이언트에 노출 가능

## 7) 즉시 확인이 필요한 리스크
- 비밀정보 노출:
  - `config.yaml`에 Turso `auth_token` 하드코딩
  - `config.yaml`에 실제 API 키 값 포함
- 운영 안정성:
  - 인메모리 레이트리밋/일일토큰 카운터로 수평 확장 시 정책 불일치
- 보안:
  - CORS 전면 허용
  - 에러 상세 메시지 외부 노출

## 8) 개선 우선순위 제안
1. `config.yaml`의 민감정보를 전부 환경변수/Secret Manager로 이전
2. 레이트리밋/토큰 사용량 저장소를 Redis 등 외부 스토리지로 전환
3. CORS 허용 도메인을 운영 도메인으로 제한
4. 사용자 응답 에러 메시지 표준화(내부 상세 숨김)
5. 스트리밍 토큰 사용량 집계 로직 보강
6. 자동 테스트 추가(인증, 레이트리밋, 스키마 파싱 실패, SSE)

## 10) 변경 이력

### 2026-03-19
**프롬프트 로딩 방식 개선 (`app/llm_service.py`, `app/database.py`)**

- **문제**: `get_llm_service()`가 순수 싱글턴이라 앱 구동 후 DB 프롬프트를 수정해도 서버 재시작 전까지 반영되지 않았음
- **변경**: TTL 기반 캐시(5분, `PROMPT_CACHE_TTL = 300`) 도입
  - 최초 요청 또는 마지막 로드 후 5분 경과 시 DB에서 프롬프트 재조회
  - 그 사이 요청은 메모리 캐시 사용 → DB 부하 최소화
  - TTL은 `PROMPT_CACHE_TTL` 상수 하나로 조정 가능
- **추가**: `database.py`의 "Successfully loaded" 로그에 실제 프롬프트 내용 포함하도록 수정

## 9) 참고 파일
- `b_reunion/main.py`
- `b_reunion/app/llm_service.py`
- `b_reunion/app/database.py`
- `b_reunion/app/rate_limiter.py`
- `b_reunion/config.yaml`
- `b_reunion/docker-compose.yml`
