#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.append(str(Path(__file__).parent.parent))

from app.database import engine, Base
from app.models.user import User
from app.models.generation import Generation, Image, ReferenceImage
from app.models.session import Session
from app.models.usage import ApiUsage


def create_tables():
    """모든 테이블 생성"""
    Base.metadata.create_all(bind=engine)
    print("✅ 데이터베이스 테이블 생성 완료")


def create_directories():
    """필요한 디렉터리 생성"""
    directories = [
        "./storage/uploads",
        "./storage/generated/originals",
        "./storage/generated/filtered", 
        "./storage/generated/resized",
        "./storage/cache",
        "./logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ 스토리지 디렉터리 생성 완료")


if __name__ == "__main__":
    print("🔧 thumbanana 데이터베이스 초기화 시작...")
    create_tables()
    create_directories()
    print("🚀 데이터베이스 초기화 완료!")