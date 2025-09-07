from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import hashlib
from datetime import datetime
from pathlib import Path
import uuid

from app.database import get_db
from app.models.generation import Generation, Image as ImageModel, ReferenceImage
from app.models.user import User
from app.services.gemini_service import GeminiService
from app.config import get_settings
from app.api.auth import get_current_user
from app.utils.i18n import get_user_language, get_api_error_message

router = APIRouter()
settings = get_settings()
gemini_service = GeminiService()


# Pydantic 모델들
from pydantic import BaseModel


class GenerateRequest(BaseModel):
    title: str
    style_preset: Optional[str] = "bold"
    variants: Optional[int] = 1
    reference_urls: Optional[List[str]] = []


class GenerateResponse(BaseModel):
    generation_id: int
    status: str
    message: str
    images: Optional[List[dict]] = None


@router.post("/", response_model=GenerateResponse)
async def generate_thumbnail(
    request: Request,
    title: str = Form(..., max_length=2000),
    style_preset: str = Form("bold"),
    variants: int = Form(1),
    reference_images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """썸네일 생성 API"""
    
    language = get_user_language(request)
    
    try:
        # 입력 검증
        if not title.strip():
            error_message = get_api_error_message("generation", "title_required", language)
            raise HTTPException(status_code=400, detail=error_message)
        
        if len(title) > 2000:
            error_message = get_api_error_message("generation", "title_too_long", language)
            raise HTTPException(status_code=400, detail=error_message)
            
        # 비로그인 사용자 제한
        if not current_user:
            if variants > 1:
                variants = 1
            if len(reference_images) > 1:
                reference_images = reference_images[:1]
        else:
            # 로그인 사용자 제한
            if variants > 3:
                variants = 3
            if len(reference_images) > 3:
                reference_images = reference_images[:3]
        
        # TODO: API 사용량 체크 (일일 한도)
        
        # 제목 요약 (200자로 제한)
        summarized_title = title[:200] if len(title) > 200 else title
        
        # 참고 이미지 처리
        reference_image_bytes = []
        reference_paths = []
        
        for ref_image in reference_images:
            # 파일 크기 검증
            if ref_image.size > settings.max_file_size:
                error_message = get_api_error_message("generation", "file_too_large", language)
                raise HTTPException(status_code=400, detail=error_message)
            
            # 파일 형식 검증
            if not ref_image.content_type.startswith('image/'):
                error_message = get_api_error_message("generation", "invalid_file_type", language)
                raise HTTPException(status_code=400, detail=error_message)
            
            # 파일 저장
            file_content = await ref_image.read()
            file_id = str(uuid.uuid4())
            file_extension = ref_image.filename.split('.')[-1] if '.' in ref_image.filename else 'jpg'
            file_path = Path(settings.upload_dir) / f"{file_id}.{file_extension}"
            
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            reference_image_bytes.append(file_content)
            reference_paths.append(str(file_path))
        
        # Generation 레코드 생성
        generation = Generation(
            user_id=current_user.id if current_user else None,
            input_title=summarized_title,
            input_script_hash=hashlib.sha256(title.encode()).hexdigest()[:16],
            style_preset=style_preset,
            reference_images_hash=hashlib.sha256(
                ''.join([hashlib.sha256(img).hexdigest() for img in reference_image_bytes]).encode()
            ).hexdigest()[:16] if reference_image_bytes else None,
            requested_variants=variants,
            status="processing"
        )
        
        db.add(generation)
        db.commit()
        db.refresh(generation)
        
        # 참고 이미지 레코드 생성
        for ref_path in reference_paths:
            ref_image_record = ReferenceImage(
                generation_id=generation.id,
                source_type="upload",
                source_path=ref_path
            )
            db.add(ref_image_record)
        
        db.commit()
        
        try:
            # Gemini API 호출
            print(f"🎨 썸네일 생성 시작: ID={generation.id}")
            results = await gemini_service.generate_thumbnail(
                title=summarized_title,
                style_preset=style_preset,
                reference_images=reference_image_bytes if reference_image_bytes else None,
                variants=variants
            )
            
            if not results:
                generation.status = "error"
                error_message = get_api_error_message("generation", "generation_failed", language)
                generation.error_message = error_message
                db.commit()
                
                raise HTTPException(status_code=500, detail=error_message)
            
            # 생성된 이미지 저장
            saved_images = []
            for i, (image_data, image_format) in enumerate(results):
                # 파일 저장
                image_id = str(uuid.uuid4())
                image_path = Path(settings.generated_dir) / "originals" / f"{image_id}.{image_format}"
                image_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(image_path, 'wb') as f:
                    f.write(image_data)
                
                # 이미지 정보 저장
                from PIL import Image as PILImage
                with PILImage.open(image_path) as img:
                    width, height = img.size
                
                image_record = ImageModel(
                    generation_id=generation.id,
                    original_path=str(image_path),
                    format=image_format,
                    width=width,
                    height=height
                )
                
                db.add(image_record)
                db.commit()
                db.refresh(image_record)
                
                saved_images.append({
                    "id": image_record.id,
                    "url": f"/api/images/{image_record.id}/download",
                    "format": image_format,
                    "width": width,
                    "height": height
                })
            
            # Generation 상태 업데이트
            generation.status = "completed"
            db.commit()
            
            print(f"✅ 썸네일 생성 완료: ID={generation.id}, 이미지 {len(saved_images)}장")
            
            success_message = get_api_error_message("generation", "generation_success", language)
            return GenerateResponse(
                generation_id=generation.id,
                status="completed", 
                message=f"{len(saved_images)}{success_message}",
                images=saved_images
            )
            
        except Exception as e:
            # 에러 상태 업데이트
            generation.status = "error"
            generation.error_message = str(e)
            db.commit()
            
            print(f"❌ 썸네일 생성 실패: {e}")
            error_message = get_api_error_message("generation", "generation_error", language)
            raise HTTPException(status_code=500, detail=error_message)
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        error_message = get_api_error_message("generation", "server_error", language)
        raise HTTPException(status_code=500, detail=error_message)


@router.get("/{generation_id}/status")
async def get_generation_status(
    generation_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """생성 상태 확인 API"""
    
    language = get_user_language(request)
    generation = db.query(Generation).filter(Generation.id == generation_id).first()
    
    if not generation:
        error_message = get_api_error_message("generation", "request_not_found", language)
        raise HTTPException(status_code=404, detail=error_message)
    
    images = []
    if generation.status == "completed":
        image_records = db.query(ImageModel).filter(ImageModel.generation_id == generation_id).all()
        images = [
            {
                "id": img.id,
                "url": f"/api/images/{img.id}/download",
                "format": img.format,
                "width": img.width,
                "height": img.height
            }
            for img in image_records
        ]
    
    return {
        "generation_id": generation.id,
        "status": generation.status,
        "error_message": generation.error_message,
        "images": images,
        "created_at": generation.created_at.isoformat(),
        "requested_variants": generation.requested_variants
    }


@router.get("/test")
async def test_gemini_connection(request: Request):
    """Gemini API 연결 테스트"""
    
    language = get_user_language(request)
    
    try:
        is_healthy = await gemini_service.health_check()
        if is_healthy:
            success_message = get_api_error_message("generation", "gemini_connection_success", language)
            return {"status": "success", "message": success_message}
        else:
            error_message = get_api_error_message("generation", "gemini_connection_failed", language)
            return {"status": "error", "message": error_message}
    except Exception as e:
        error_message = get_api_error_message("generation", "test_failed", language, error=str(e))
        return {"status": "error", "message": error_message}