from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pathlib import Path

from app.config import get_settings
from app.database import engine, Base
from app.utils.i18n import get_user_language, get_translations

settings = get_settings()

# FastAPI 앱 생성
app = FastAPI(
    title="thumbanana",
    description="AI-powered YouTube Thumbnail Generator using Gemini 2.5 Flash Image",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts,
)

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# API 라우터 등록
from app.api import generate, images, auth, history
app.include_router(generate.router, prefix="/api/generate", tags=["generation"])
app.include_router(images.router, prefix="/api/images", tags=["images"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(history.router, prefix="/api/history", tags=["history"])

# 다국어 템플릿 렌더링 헬퍼
def render_localized_template(template_name: str, request: Request, **context):
    """다국어 지원 템플릿 렌더링"""
    language = get_user_language(request)
    translations = get_translations(language)
    
    context.update({
        "request": request,
        "lang": language,
        "t": translations
    })
    
    return templates.TemplateResponse(template_name, context)

# 메인 페이지
@app.get("/")
async def home(request: Request):
    return render_localized_template("index.html", request)

# 영어 버전 메인 페이지
@app.get("/en")
async def home_en(request: Request):
    # 영어로 강제 설정
    translations = get_translations("en")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "lang": "en", 
        "t": translations
    })

# 인증 페이지들
@app.get("/login")
async def login_page(request: Request):
    return render_localized_template("auth/login.html", request)

@app.get("/register") 
async def register_page(request: Request):
    return render_localized_template("auth/register.html", request)

@app.get("/history")
async def history_page(request: Request):
    return render_localized_template("history.html", request)

# 영어 버전 페이지들
@app.get("/en/login")
async def login_page_en(request: Request):
    translations = get_translations("en")
    return templates.TemplateResponse("auth/login.html", {
        "request": request, "lang": "en", "t": translations
    })

@app.get("/en/register")
async def register_page_en(request: Request):
    translations = get_translations("en")
    return templates.TemplateResponse("auth/register.html", {
        "request": request, "lang": "en", "t": translations
    })

@app.get("/en/history")
async def history_page_en(request: Request):
    translations = get_translations("en")
    return templates.TemplateResponse("history.html", {
        "request": request, "lang": "en", "t": translations
    })

# 헬스 체크
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "thumbanana", "version": "1.0.0"}

# 애플리케이션 시작 이벤트
@app.on_event("startup")
async def startup_event():
    # 데이터베이스 테이블 생성
    Base.metadata.create_all(bind=engine)
    
    # 스토리지 디렉터리 생성
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.generated_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.cache_dir).mkdir(parents=True, exist_ok=True)
    Path("./logs").mkdir(parents=True, exist_ok=True)
    
    print("🚀 thumbanana 서버 시작 완료!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )