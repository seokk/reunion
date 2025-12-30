FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 전체 코드 복사 (하위 app 디렉토리 만들지 않음)
COPY . .

RUN mkdir -p logs

# EXPOSE는 문서화 목적으로 남겨둘 수 있지만, Cloud Run에서는 무시됩니다.
# Cloud Run은 PORT 환경 변수로 지정된 포트를 사용합니다.
EXPOSE 8080

# main.py를 직접 실행하여 PORT 환경 변수를 동적으로 읽도록 합니다.
CMD ["python", "main.py"]
