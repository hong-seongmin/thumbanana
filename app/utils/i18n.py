import json
import os
from typing import Dict, Any, Optional
from functools import lru_cache
from pathlib import Path

# 번역 파일 경로
I18N_DIR = Path(__file__).parent.parent / "i18n"

# 지원하는 언어 목록
SUPPORTED_LANGUAGES = ["ko", "en"]
DEFAULT_LANGUAGE = "ko"


@lru_cache(maxsize=10)
def load_translations(language: str) -> Dict[str, Any]:
    """번역 파일 로드 및 캐싱"""
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
        
    translation_file = I18N_DIR / f"{language}.json"
    
    try:
        with open(translation_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Translation file not found: {translation_file}")
        # 기본 언어로 폴백
        if language != DEFAULT_LANGUAGE:
            return load_translations(DEFAULT_LANGUAGE)
        return {}
    except json.JSONDecodeError as e:
        print(f"⚠️ Invalid JSON in translation file: {translation_file} - {e}")
        return {}


def get_user_language(request) -> str:
    """요청에서 사용자 언어 감지"""
    # URL 경로에서 언어 확인 (예: /en/)
    path = request.url.path
    if path.startswith('/en'):
        return 'en'
    
    # Accept-Language 헤더에서 언어 감지
    accept_language = request.headers.get('accept-language', '')
    
    # 영어 선호도 확인
    if 'en' in accept_language.lower():
        # 영어가 한국어보다 우선순위가 높은지 확인
        languages = []
        for lang_part in accept_language.lower().split(','):
            lang_part = lang_part.strip()
            if ';q=' in lang_part:
                lang, quality = lang_part.split(';q=')
                try:
                    languages.append((lang.strip(), float(quality)))
                except ValueError:
                    languages.append((lang.strip(), 1.0))
            else:
                languages.append((lang_part, 1.0))
        
        # 품질 점수로 정렬
        languages.sort(key=lambda x: x[1], reverse=True)
        
        # 지원하는 언어 중 가장 우선순위 높은 것 선택
        for lang, _ in languages:
            if lang.startswith('en'):
                return 'en'
            elif lang.startswith('ko'):
                return 'ko'
    
    # 기본값 반환
    return DEFAULT_LANGUAGE


class TranslationDict:
    """번역 딕셔너리 래퍼 - 점 표기법으로 중첩 접근 지원"""
    
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    def __getattr__(self, key: str):
        if key.startswith('_'):
            return super().__getattribute__(key)
            
        value = self._data.get(key, key)
        if isinstance(value, dict):
            return TranslationDict(value)
        return value
    
    def __getitem__(self, key: str):
        return self.__getattr__(key)
    
    def get(self, key: str, default: str = None):
        """안전한 키 접근"""
        try:
            return self.__getattr__(key)
        except (KeyError, AttributeError):
            return default or key


def get_translations(language: str) -> TranslationDict:
    """번역 딕셔너리 객체 반환"""
    translations = load_translations(language)
    return TranslationDict(translations)


def get_localized_message(message_key: str, language: str, **kwargs) -> str:
    """다국어 메시지 포매팅"""
    translations = load_translations(language)
    
    # messages 섹션에서 메시지 찾기
    message = translations.get('messages', {}).get(message_key, message_key)
    
    # 포매팅 적용
    if kwargs:
        try:
            return message.format(**kwargs)
        except (KeyError, ValueError):
            return message
    
    return message


def get_api_error_message(category: str, error_key: str, language: str, **kwargs) -> str:
    """API 오류 메시지 반환"""
    translations = load_translations(language)
    
    # api_errors 섹션에서 메시지 찾기
    api_errors = translations.get('api_errors', {})
    category_errors = api_errors.get(category, {})
    message = category_errors.get(error_key, f"{category}.{error_key}")
    
    # 포매팅 적용
    if kwargs:
        try:
            return message.format(**kwargs)
        except (KeyError, ValueError):
            return message
    
    return message


# 템플릿에서 사용할 헬퍼 함수들
def get_page_title(page_key: str, language: str) -> str:
    """페이지별 타이틀 반환"""
    translations = load_translations(language)
    meta = translations.get('meta', {})
    
    title_key = f"page_title_{page_key}" if page_key else "page_title"
    return meta.get(title_key, meta.get('page_title', 'thumbanana'))


def get_meta_description(language: str) -> str:
    """메타 설명 반환"""
    translations = load_translations(language)
    return translations.get('meta', {}).get('description', '')


def get_meta_keywords(language: str) -> str:
    """메타 키워드 반환"""
    translations = load_translations(language)
    return translations.get('meta', {}).get('keywords', '')