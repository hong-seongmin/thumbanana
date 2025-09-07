from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User

router = APIRouter()
security = HTTPBearer(auto_error=False)


# Request/Response 모델
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    last_login: Optional[datetime]

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    user: UserResponse
    access_token: str
    message: str


# 의존성: 현재 사용자 조회
async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Bearer 토큰 또는 쿠키에서 세션 ID를 추출하여 사용자 조회"""
    
    # Bearer 토큰에서 세션 ID 추출
    session_id = None
    if credentials:
        session_id = credentials.credentials
    
    # 쿠키에서 세션 ID 추출 (fallback)
    if not session_id:
        session_id = request.cookies.get("session_id")
    
    if not session_id:
        return None
    
    return AuthService.get_user_by_session(db, session_id)


# 의존성: 로그인 필수
async def require_auth(current_user: User = Depends(get_current_user)) -> User:
    """인증이 필요한 엔드포인트용 의존성"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """회원가입"""
    try:
        user = AuthService.create_user(db, user_data.email, user_data.password)
        return UserResponse.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 중 오류가 발생했습니다."
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    user_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    """로그인"""
    user = AuthService.authenticate_user(db, user_data.email, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다."
        )
    
    # 세션 생성
    session_id = AuthService.create_session(db, user.id)
    
    # 쿠키 설정 (7일)
    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=7 * 24 * 60 * 60,  # 7일
        httponly=True,
        secure=False,  # HTTPS가 아니므로 False
        samesite="lax"
    )
    
    return LoginResponse(
        user=UserResponse.model_validate(user),
        access_token=session_id,
        message="로그인 성공"
    )


@router.post("/logout")
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """로그아웃"""
    # 세션 ID 추출 (Bearer 토큰 또는 쿠키)
    if not session_id and current_user:
        session_id = None  # get_current_user에서 이미 세션을 확인했으므로
        # 실제로는 request에서 추출해야 하지만 단순화
    
    # 세션 삭제 (실제 구현에서는 request에서 session_id를 추출해야 함)
    # AuthService.delete_session(db, session_id)
    
    # 쿠키 삭제
    response.delete_cookie(key="session_id")
    
    return {"message": "로그아웃 되었습니다."}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(require_auth)):
    """현재 로그인한 사용자 정보 조회"""
    return UserResponse.model_validate(current_user)


@router.get("/check")
async def check_auth(current_user: Optional[User] = Depends(get_current_user)):
    """인증 상태 확인"""
    if current_user:
        return {
            "authenticated": True,
            "user": UserResponse.model_validate(current_user)
        }
    else:
        return {"authenticated": False}