import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from pathlib import Path
from app.config import get_settings

settings = get_settings()


class CacheService:
    """간단한 파일 기반 캐시 서비스"""
    
    def __init__(self):
        self.cache_dir = Path(settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = settings.cache_ttl
        
    def _get_cache_path(self, key: str) -> Path:
        """캐시 키를 파일 경로로 변환"""
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed_key}.json"
    
    def _is_expired(self, timestamp: str) -> bool:
        """캐시가 만료되었는지 확인"""
        cached_time = datetime.fromisoformat(timestamp)
        return datetime.now() - cached_time > timedelta(seconds=self.ttl)
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
            
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # 만료 확인
            if self._is_expired(cache_data['timestamp']):
                await self.delete(key)
                return None
                
            # base64 데이터를 bytes로 디코딩
            value = cache_data['value']
            if isinstance(value, list):
                decoded_value = []
                for item in value:
                    if isinstance(item, list) and len(item) == 2:
                        encoded_data, image_format = item
                        if isinstance(encoded_data, str):
                            # base64를 bytes로 디코딩
                            import base64
                            decoded_data = base64.b64decode(encoded_data)
                            decoded_value.append((decoded_data, image_format))
                        else:
                            decoded_value.append(tuple(item))
                    else:
                        decoded_value.append(item)
                return decoded_value
            else:
                return value
        except (json.JSONDecodeError, KeyError, IOError):
            # 손상된 캐시 파일 삭제
            await self.delete(key)
            return None
    
    async def set(self, key: str, value: Any) -> bool:
        """캐시에 값 저장"""
        cache_path = self._get_cache_path(key)
        
        # bytes 데이터를 base64로 인코딩
        serializable_value = []
        if isinstance(value, list):
            for item in value:
                if isinstance(item, tuple) and len(item) == 2:
                    image_data, image_format = item
                    if isinstance(image_data, bytes):
                        # bytes를 base64로 인코딩
                        import base64
                        encoded_data = base64.b64encode(image_data).decode('utf-8')
                        serializable_value.append([encoded_data, image_format])
                    else:
                        serializable_value.append(item)
                else:
                    serializable_value.append(item)
        else:
            serializable_value = value
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'value': serializable_value,
            'key': key  # 디버깅용
        }
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            return True
        except (IOError, TypeError) as e:
            print(f"캐시 저장 실패: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        cache_path = self._get_cache_path(key)
        
        try:
            if cache_path.exists():
                cache_path.unlink()
            return True
        except IOError:
            return False
    
    async def clear_expired(self) -> int:
        """만료된 캐시 파일들 정리"""
        cleaned = 0
        
        for cache_file in self.cache_dir.glob('*.json'):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                if self._is_expired(cache_data['timestamp']):
                    cache_file.unlink()
                    cleaned += 1
                    
            except (json.JSONDecodeError, KeyError, IOError):
                # 손상된 파일 삭제
                cache_file.unlink()
                cleaned += 1
                
        return cleaned
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보"""
        cache_files = list(self.cache_dir.glob('*.json'))
        total_files = len(cache_files)
        expired_files = 0
        total_size = 0
        
        for cache_file in cache_files:
            try:
                total_size += cache_file.stat().st_size
                
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                if self._is_expired(cache_data['timestamp']):
                    expired_files += 1
                    
            except (json.JSONDecodeError, KeyError, IOError):
                expired_files += 1
                
        return {
            'total_files': total_files,
            'expired_files': expired_files,
            'valid_files': total_files - expired_files,
            'total_size_bytes': total_size,
            'cache_directory': str(self.cache_dir)
        }