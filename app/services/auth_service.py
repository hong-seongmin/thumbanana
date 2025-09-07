import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.session import Session as UserSession
from app.database import get_db


class AuthService:
    """사용자 인증 및 세션 관리 서비스"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """비밀번호를 해시화"""
        salt = secrets.token_hex(32)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return f"{salt}:{pwd_hash.hex()}"
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """비밀번호 검증"""
        try:
            salt, stored_hash = password_hash.split(':')
            pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return pwd_hash.hex() == stored_hash
        except ValueError:
            return False
    
    @staticmethod
    def create_user(db: Session, email: str, password: str) -> User:
        """새 사용자 생성"""
        # 이메일 중복 확인
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 등록된 이메일입니다."
            )
        
        # 비밀번호 유효성 검사
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="비밀번호는 최소 8자 이상이어야 합니다."
            )
        
        # 사용자 생성
        password_hash = AuthService.hash_password(password)
        user = User(
            email=email,
            password_hash=password_hash
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return user
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """사용자 인증"""
        user = db.query(User).filter(User.email == email).first()
        if not user or not AuthService.verify_password(password, user.password_hash):
            return None
        
        # 마지막 로그인 시간 업데이트
        user.last_login = datetime.now()
        db.commit()
        
        return user
    
    @staticmethod
    def create_session(db: Session, user_id: int, expires_hours: int = 24 * 7) -> str:
        """세션 생성 (7일 기본)"""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        session = UserSession(
            id=session_id,
            user_id=user_id,
            expires_at=expires_at
        )
        
        db.add(session)
        db.commit()
        
        return session_id
    
    @staticmethod
    def get_user_by_session(db: Session, session_id: str) -> Optional[User]:
        """세션으로 사용자 조회"""
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        
        if not session:
            return None
        
        # 세션 만료 확인
        if session.expires_at < datetime.now():
            # 만료된 세션 삭제
            db.delete(session)
            db.commit()
            return None
        
        return session.user
    
    @staticmethod
    def delete_session(db: Session, session_id: str) -> bool:
        """세션 삭제 (로그아웃)"""
        session = db.query(UserSession).filter(UserSession.id == session_id).first()
        if session:
            db.delete(session)
            db.commit()
            return True
        return False
    
    @staticmethod
    def cleanup_expired_sessions(db: Session) -> int:
        """만료된 세션 정리"""
        expired_sessions = db.query(UserSession).filter(
            UserSession.expires_at < datetime.now()
        ).all()
        
        count = len(expired_sessions)
        for session in expired_sessions:
            db.delete(session)
        
        db.commit()
        return count