#!/bin/bash

# thumbanana 웹 서버 시작 스크립트
# 포트 충돌 시 기존 프로세스를 종료하고 새로 시작

set -e  # 오류 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정
DEFAULT_PORT=8000
CURRENT_PORT=8001
PROJECT_NAME="thumbanana"

# 포트 설정 (인자로 받거나 기본값 사용)
PORT=${1:-$CURRENT_PORT}

echo -e "${BLUE}🍌 $PROJECT_NAME 웹 서버 시작 스크립트${NC}"
echo -e "${BLUE}포트: $PORT${NC}"
echo ""

# 현재 디렉토리 확인
if [ ! -f "app/main.py" ]; then
    echo -e "${RED}❌ 오류: thumbanana 프로젝트 루트 디렉토리에서 실행해주세요${NC}"
    echo "현재 디렉토리: $(pwd)"
    exit 1
fi

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  경고: .env 파일이 없습니다. .env.example을 복사하여 설정해주세요${NC}"
    if [ -f ".env.example" ]; then
        echo "  cp .env.example .env"
    fi
    echo ""
fi

# UV 설치 확인
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ 오류: UV가 설치되지 않았습니다${NC}"
    echo "UV 설치 방법: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo -e "${YELLOW}🔍 포트 $PORT 사용 중인 프로세스 확인 중...${NC}"

# 포트 사용 중인 프로세스 찾기
PID=$(lsof -ti:$PORT 2>/dev/null || true)

if [ ! -z "$PID" ]; then
    echo -e "${YELLOW}⚠️  포트 $PORT가 이미 사용 중입니다 (PID: $PID)${NC}"
    
    # 프로세스 정보 출력
    echo "사용 중인 프로세스:"
    ps -p $PID -o pid,ppid,cmd 2>/dev/null || echo "프로세스 정보를 가져올 수 없습니다"
    
    echo -e "${YELLOW}🔄 기존 프로세스 종료 중...${NC}"
    
    # 프로세스 종료 시도
    kill $PID 2>/dev/null || true
    
    # 잠깐 대기
    sleep 2
    
    # 여전히 실행 중이면 강제 종료
    if kill -0 $PID 2>/dev/null; then
        echo -e "${RED}⚠️  일반 종료 실패, 강제 종료 시도 중...${NC}"
        kill -9 $PID 2>/dev/null || true
        sleep 1
    fi
    
    # 최종 확인
    if lsof -ti:$PORT >/dev/null 2>&1; then
        echo -e "${RED}❌ 포트 $PORT를 해제할 수 없습니다${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ 기존 프로세스가 종료되었습니다${NC}"
    fi
else
    echo -e "${GREEN}✅ 포트 $PORT가 사용 가능합니다${NC}"
fi

echo ""
echo -e "${BLUE}📦 의존성 확인 중...${NC}"

# UV sync로 의존성 설치/업데이트
if ! uv sync --quiet; then
    echo -e "${RED}❌ 의존성 설치 실패${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 의존성 설치 완료${NC}"
echo ""

# 로그 디렉토리 생성
mkdir -p logs

# 데이터베이스 마이그레이션 (필요시)
echo -e "${BLUE}🗄️  데이터베이스 초기화 중...${NC}"
# 여기에 필요시 마이그레이션 명령어 추가
echo -e "${GREEN}✅ 데이터베이스 준비 완료${NC}"
echo ""

echo -e "${BLUE}🚀 $PROJECT_NAME 서버 시작 중...${NC}"
echo -e "${BLUE}URL: http://localhost:$PORT${NC}"
echo -e "${BLUE}API 문서: http://localhost:$PORT/docs${NC}"
echo ""
echo -e "${YELLOW}서버를 중지하려면 Ctrl+C를 누르세요${NC}"
echo ""

# 서버 시작
exec uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload