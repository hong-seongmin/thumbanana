# 🚀 thumbanana 서버 시작 방법

## 빠른 시작

### Linux/Mac
```bash
./start.sh
```

### Windows
```cmd
start.bat
```

## 사용자 정의 포트

### Linux/Mac
```bash
./start.sh 8080    # 8080 포트로 시작
```

### Windows
```cmd
start.bat 8080     # 8080 포트로 시작
```

## 스크립트 기능

✅ **자동 포트 관리**: 기존 프로세스가 포트를 사용 중이면 자동으로 종료  
✅ **의존성 검사**: UV와 필요한 패키지들 자동 설치/업데이트  
✅ **환경 검증**: .env 파일과 프로젝트 구조 확인  
✅ **데이터베이스 초기화**: 필요한 디렉토리 및 데이터베이스 준비  
✅ **컬러 출력**: 상태별 색상으로 명확한 피드백  

## 서버 접속

- **메인 페이지**: http://localhost:8001
- **영어 페이지**: http://localhost:8001/en  
- **API 문서**: http://localhost:8001/docs
- **히스토리**: http://localhost:8001/history (로그인 필요)

## 문제 해결

### UV가 없다는 오류가 나는 경우
```bash
# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### .env 파일 설정
```bash
# .env.example이 있는 경우
cp .env.example .env

# 수동으로 생성하는 경우
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

### 포트 변경이 필요한 경우
기본 포트(8001)가 사용 중이면 다른 포트 지정:
```bash
./start.sh 8080
```

## 개발 모드

스크립트는 자동으로 `--reload` 모드로 실행되어 코드 변경 시 자동 재시작됩니다.

## 서버 중지

터미널에서 `Ctrl + C` 를 누르면 서버가 안전하게 종료됩니다.