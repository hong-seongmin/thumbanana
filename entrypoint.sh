#!/bin/bash
set -e

echo "🍌 thumbanana Docker Container Starting..."

# 필요한 디렉토리 생성
echo "📁 Creating necessary directories..."
mkdir -p /app/data
mkdir -p /app/storage/uploads
mkdir -p /app/storage/generated
mkdir -p /app/storage/cache  
mkdir -p /app/logs

# 데이터베이스 파일 권한 설정
echo "🗄️ Setting up database..."
if [ ! -f "/app/data/thumbanana.db" ]; then
    echo "📋 Creating new database file..."
    touch /app/data/thumbanana.db
fi

# 파일 권한 설정
chmod 666 /app/data/thumbanana.db
chmod 755 /app/data
chmod -R 755 /app/storage
chmod -R 755 /app/logs

echo "✅ Directory setup complete"

# 환경 변수 확인
echo "🔧 Environment check..."
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  WARNING: GEMINI_API_KEY is not set"
else
    echo "✅ GEMINI_API_KEY is configured"
fi

echo "🚀 Starting thumbanana application..."

# 애플리케이션 시작
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000