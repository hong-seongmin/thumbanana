from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Gemini API
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash-image-preview"
    
    # App
    secret_key: str
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database  
    database_url: str = "sqlite:////app/data/thumbanana.db"
    
    # Storage
    upload_dir: str = "./storage/uploads"
    generated_dir: str = "./storage/generated"
    cache_dir: str = "./storage/cache"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # Rate Limiting
    daily_request_limit_guest: int = 3
    daily_request_limit_user: int = 10
    daily_request_limit_global: int = 100
    
    # Security
    access_token_expire_minutes: int = 30
    allowed_hosts: List[str] = ["*"]
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    # Cache
    cache_ttl: int = 180  # 3 minutes  
    cache_max_size: int = 1000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings():
    return Settings()