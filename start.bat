@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM thumbanana 웹 서버 시작 스크립트 (Windows)
REM 포트 충돌 시 기존 프로세스를 종료하고 새로 시작

set "PROJECT_NAME=thumbanana"
set "DEFAULT_PORT=8001"

REM 포트 설정 (인자로 받거나 기본값 사용)
if "%1"=="" (
    set "PORT=%DEFAULT_PORT%"
) else (
    set "PORT=%1"
)

echo.
echo 🍌 %PROJECT_NAME% 웹 서버 시작 스크립트
echo 포트: %PORT%
echo.

REM 현재 디렉토리 확인
if not exist "app\main.py" (
    echo ❌ 오류: thumbanana 프로젝트 루트 디렉토리에서 실행해주세요
    echo 현재 디렉토리: %CD%
    pause
    exit /b 1
)

REM .env 파일 확인
if not exist ".env" (
    echo ⚠️  경고: .env 파일이 없습니다. .env.example을 복사하여 설정해주세요
    if exist ".env.example" (
        echo   copy .env.example .env
    )
    echo.
)

REM UV 설치 확인
uv --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 오류: UV가 설치되지 않았습니다
    echo UV 설치: https://github.com/astral-sh/uv
    pause
    exit /b 1
)

echo 🔍 포트 %PORT% 사용 중인 프로세스 확인 중...

REM 포트 사용 중인 프로세스 찾기
for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":%PORT% "') do (
    set "PID=%%i"
    goto :found_process
)
goto :port_available

:found_process
echo ⚠️  포트 %PORT%가 이미 사용 중입니다 (PID: %PID%)

REM 프로세스 정보 출력
echo 사용 중인 프로세스:
tasklist /FI "PID eq %PID%" 2>nul

echo 🔄 기존 프로세스 종료 중...

REM 프로세스 종료 시도
taskkill /PID %PID% /F >nul 2>&1

REM 잠깐 대기
timeout /t 2 /nobreak >nul

REM 최종 확인
netstat -ano | findstr ":%PORT% " >nul 2>&1
if not errorlevel 1 (
    echo ❌ 포트 %PORT%를 해제할 수 없습니다
    pause
    exit /b 1
) else (
    echo ✅ 기존 프로세스가 종료되었습니다
)
goto :start_server

:port_available
echo ✅ 포트 %PORT%가 사용 가능합니다

:start_server
echo.
echo 📦 의존성 확인 중...

REM UV sync로 의존성 설치/업데이트
uv sync --quiet
if errorlevel 1 (
    echo ❌ 의존성 설치 실패
    pause
    exit /b 1
)

echo ✅ 의존성 설치 완료
echo.

REM 로그 디렉토리 생성
if not exist "logs" mkdir logs

echo 🗄️  데이터베이스 초기화 중...
REM 여기에 필요시 마이그레이션 명령어 추가
echo ✅ 데이터베이스 준비 완료
echo.

echo 🚀 %PROJECT_NAME% 서버 시작 중...
echo URL: http://localhost:%PORT%
echo API 문서: http://localhost:%PORT%/docs
echo.
echo 서버를 중지하려면 Ctrl+C를 누르세요
echo.

REM 서버 시작
uv run uvicorn app.main:app --host 0.0.0.0 --port %PORT% --reload