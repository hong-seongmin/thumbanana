from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
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
    title: str = Form(..., max_length=2000),
    style_preset: str = Form("bold"),
    variants: int = Form(1),
    reference_images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """썸네일 생성 API"""
    
    try:
        # 입력 검증
        if not title.strip():
            raise HTTPException(status_code=400, detail="제목은 필수 입력 항목입니다.")
        
        if len(title) > 2000:
            raise HTTPException(status_code=400, detail="제목은 2000자 이하로 입력해주세요.")
            
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
                raise HTTPException(
                    status_code=400, 
                    detail=f"참고 이미지 크기는 {settings.max_file_size // (1024*1024)}MB 이하여야 합니다."
                )
            
            # 파일 형식 검증
            if not ref_image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")
            
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
                generation.error_message = "이미지 생성에 실패했습니다."
                db.commit()
                
                raise HTTPException(status_code=500, detail="썸네일 생성에 실패했습니다. 다시 시도해주세요.")
            
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
            
            return GenerateResponse(
                generation_id=generation.id,
                status="completed",
                message=f"{len(saved_images)}장의 썸네일이 성공적으로 생성되었습니다.",
                images=saved_images
            )
            
        except Exception as e:
            # 에러 상태 업데이트
            generation.status = "error"
            generation.error_message = str(e)
            db.commit()
            
            print(f"❌ 썸네일 생성 실패: {e}")
            raise HTTPException(status_code=500, detail="썸네일 생성 중 오류가 발생했습니다.")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")


@router.get("/{generation_id}/status")
async def get_generation_status(
    generation_id: int,
    db: Session = Depends(get_db)
):
    """생성 상태 확인 API"""
    
    generation = db.query(Generation).filter(Generation.id == generation_id).first()
    
    if not generation:
        raise HTTPException(status_code=404, detail="생성 요청을 찾을 수 없습니다.")
    
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
async def test_gemini_connection():
    """Gemini API 연결 테스트"""
    
    try:
        is_healthy = await gemini_service.health_check()
        if is_healthy:
            return {"status": "success", "message": "Gemini API 연결 정상"}
        else:
            return {"status": "error", "message": "Gemini API 연결 실패"}
    except Exception as e:
        return {"status": "error", "message": f"테스트 실패: {str(e)}"}