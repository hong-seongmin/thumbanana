# 🐳 Docker로 thumbanana 실행하기

## 빠른 시작

### 1. 환경변수 설정
```bash
cp .env.example .env
# .env 파일을 편집하여 GEMINI_API_KEY 설정
```

### 2. Docker Compose로 실행
```bash
docker-compose up -d
```

### 3. 서비스 확인
- **메인 페이지**: http://localhost:8000
- **영어 페이지**: http://localhost:8000/en  
- **API 문서**: http://localhost:8000/docs
- **헬스 체크**: http://localhost:8000/api/health

## 상세 명령어

### 🚀 서비스 시작
```bash
# 백그라운드에서 실행
docker-compose up -d

# 포그라운드에서 실행 (로그 확인)
docker-compose up
```

### 📊 서비스 상태 확인
```bash
# 서비스 상태
docker-compose ps

# 로그 확인
docker-compose logs -f thumbanana

# 컨테이너 내부 접속
docker-compose exec thumbanana bash
```

### 🔄 서비스 관리
```bash
# 서비스 중지
docker-compose stop

# 서비스 재시작
docker-compose restart

# 서비스 완전 종료 (볼륨 유지)
docker-compose down

# 서비스 완전 종료 (볼륨 삭제)
docker-compose down -v
```

### 🔧 개발 모드

개발 중에는 코드 변경사항을 즉시 반영하기 위해 볼륨 마운트를 추가할 수 있습니다:

```yaml
# docker-compose.override.yml 파일 생성
version: '3.8'
services:
  thumbanana:
    volumes:
      - .:/app
    environment:
      - DEBUG=True
    command: ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 🏗️ 이미지 빌드

```bash
# 이미지 다시 빌드
docker-compose build

# 캐시 없이 빌드
docker-compose build --no-cache

# 빌드 후 실행
docker-compose up --build
```

## 환경변수

주요 환경변수들은 `.env` 파일에서 설정할 수 있습니다:

```bash
# 필수 설정
GEMINI_API_KEY=your-api-key-here

# 선택적 설정
DEBUG=False
SECRET_KEY=your-secret-key
DAILY_REQUEST_LIMIT_GUEST=3
DAILY_REQUEST_LIMIT_USER=10
```

## 볼륨

Docker Compose는 다음 볼륨들을 관리합니다:

- `./storage` → `/app/storage`: 업로드된 이미지와 생성된 썸네일
- `./logs` → `/app/logs`: 애플리케이션 로그
- `./thumbanana.db` → `/app/thumbanana.db`: SQLite 데이터베이스

## 헬스체크

컨테이너는 30초마다 헬스체크를 수행합니다:
```bash
# 헬스체크 상태 확인
docker-compose ps
```

## 트러블슈팅

### 포트 충돌
```bash
# 다른 포트로 실행
docker-compose -f docker-compose.yml up -d
# 또는 docker-compose.yml에서 ports를 "8080:8000"으로 변경
```

### 권한 문제
```bash
# 스토리지 디렉토리 권한 설정
sudo chown -R $USER:$USER storage logs
chmod -R 755 storage logs
```

### 로그 확인
```bash
# 실시간 로그
docker-compose logs -f

# 최근 로그만
docker-compose logs --tail=100
```

### 컨테이너 재시작
```bash
# 특정 서비스만 재시작
docker-compose restart thumbanana
```