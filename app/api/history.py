from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from app.database import get_db
from app.models.generation import Generation, Image as ImageModel
from app.models.user import User
from app.api.auth import require_auth

router = APIRouter()


@router.get("/")
async def get_user_history(
    current_user: User = Depends(require_auth),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(10, ge=1, le=50, description="페이지당 항목 수"),
    db: Session = Depends(get_db)
):
    """사용자 생성 히스토리 조회 (실제 데이터베이스 기반 페이지네이션)"""
    
    # 오프셋 계산
    offset = (page - 1) * limit
    
    # 사용자별 생성 이력 조회 (이미지 포함, 실제 DB 쿼리)
    generations = db.query(Generation)\
        .options(joinedload(Generation.images))\
        .filter(Generation.user_id == current_user.id)\
        .order_by(desc(Generation.created_at))\
        .offset(offset)\
        .limit(limit)\
        .all()
    
    # 총 개수 조회 (실제 DB 카운트)
    total = db.query(Generation)\
        .filter(Generation.user_id == current_user.id)\
        .count()
    
    # 실제 데이터 구성
    items = []
    for gen in generations:
        # 실제 이미지 정보 구성
        images = []
        for img in gen.images:
            images.append({
                "id": img.id,
                "url": f"/api/images/{img.id}/download",
                "format": img.format,
                "width": img.width,
                "height": img.height
            })
        
        items.append({
            "id": gen.id,
            "title": gen.input_title,
            "style_preset": gen.style_preset,
            "status": gen.status,
            "variants_requested": gen.requested_variants,
            "created_at": gen.created_at.isoformat(),
            "images": images
        })
    
    # 페이지네이션 메타데이터
    total_pages = (total + limit - 1) // limit
    
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages
        },
        "user": {
            "id": current_user.id,
            "email": current_user.email
        }
    }


@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """사용자 통계 정보 (실제 DB 기반)"""
    
    # 총 생성 횟수
    total_generations = db.query(Generation)\
        .filter(Generation.user_id == current_user.id)\
        .count()
    
    # 성공한 생성 횟수
    completed_generations = db.query(Generation)\
        .filter(Generation.user_id == current_user.id, 
                Generation.status == "completed")\
        .count()
    
    # 총 생성된 이미지 수
    total_images = db.query(ImageModel)\
        .join(Generation)\
        .filter(Generation.user_id == current_user.id)\
        .count()
    
    # 첫 번째 생성일
    first_generation = db.query(Generation)\
        .filter(Generation.user_id == current_user.id)\
        .order_by(Generation.created_at)\
        .first()
    
    # 최근 생성일
    last_generation = db.query(Generation)\
        .filter(Generation.user_id == current_user.id)\
        .order_by(desc(Generation.created_at))\
        .first()
    
    return {
        "total_generations": total_generations,
        "completed_generations": completed_generations,
        "success_rate": round(completed_generations / total_generations * 100, 1) if total_generations > 0 else 0,
        "total_images": total_images,
        "first_generation": first_generation.created_at.isoformat() if first_generation else None,
        "last_generation": last_generation.created_at.isoformat() if last_generation else None,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "member_since": current_user.created_at.isoformat()
        }
    }


@router.delete("/{generation_id}")
async def delete_generation(
    generation_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """특정 생성 기록 삭제 (실제 DB에서 삭제)"""
    
    # 해당 생성 기록 조회 (소유자 확인)
    generation = db.query(Generation)\
        .filter(Generation.id == generation_id, 
                Generation.user_id == current_user.id)\
        .first()
    
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 생성 기록을 찾을 수 없습니다."
        )
    
    # 관련 이미지 파일들도 실제로 삭제
    import os
    from pathlib import Path
    
    for image in generation.images:
        try:
            # 실제 파일 삭제
            if os.path.exists(image.original_path):
                os.remove(image.original_path)
            if image.filtered_path and os.path.exists(image.filtered_path):
                os.remove(image.filtered_path)
            if image.resized_path and os.path.exists(image.resized_path):
                os.remove(image.resized_path)
        except Exception as e:
            print(f"파일 삭제 실패: {e}")
    
    # DB에서 삭제 (CASCADE로 관련 이미지 레코드도 함께 삭제)
    db.delete(generation)
    db.commit()
    
    return {"message": "생성 기록이 삭제되었습니다.", "generation_id": generation_id}


@router.post("/{generation_id}/regenerate")
async def regenerate_thumbnail(
    generation_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """기존 생성 기록을 바탕으로 재생성 (실제 Gemini API 호출)"""
    
    # 원본 생성 기록 조회
    original_generation = db.query(Generation)\
        .filter(Generation.id == generation_id, 
                Generation.user_id == current_user.id)\
        .first()
    
    if not original_generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 생성 기록을 찾을 수 없습니다."
        )
    
    # 참고 이미지 로딩
    reference_images = []
    for ref_img in original_generation.reference_images:
        try:
            with open(ref_img.source_path, 'rb') as f:
                reference_images.append(f.read())
        except:
            continue
    
    # 새로운 생성 요청으로 리다이렉트
    from app.services.gemini_service import GeminiService
    import uuid
    
    gemini_service = GeminiService()
    
    try:
        # 실제 Gemini API 호출
        results = await gemini_service.generate_thumbnail(
            title=original_generation.input_title,
            style_preset=original_generation.style_preset,
            reference_images=reference_images if reference_images else None,
            variants=original_generation.requested_variants
        )
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="재생성에 실패했습니다."
            )
        
        # 새로운 Generation 레코드 생성
        new_generation = Generation(
            user_id=current_user.id,
            input_title=original_generation.input_title,
            style_preset=original_generation.style_preset,
            requested_variants=original_generation.requested_variants,
            status="completed"
        )
        
        db.add(new_generation)
        db.commit()
        db.refresh(new_generation)
        
        # 새로운 이미지들 저장
        saved_images = []
        for i, (image_data, image_format) in enumerate(results):
            from app.config import get_settings
            settings = get_settings()
            
            # 파일 저장
            image_id = str(uuid.uuid4())
            image_path = Path(settings.generated_dir) / "originals" / f"{image_id}.{image_format}"
            image_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            # 이미지 크기 확인
            from PIL import Image as PILImage
            with PILImage.open(image_path) as img:
                width, height = img.size
            
            # DB 저장
            image_record = ImageModel(
                generation_id=new_generation.id,
                original_path=str(image_path),
                format=image_format,
                width=width,
                height=height
            )
            
            db.add(image_record)
            saved_images.append({
                "id": image_record.id,
                "url": f"/api/images/{image_record.id}/download",
                "format": image_format,
                "width": width,
                "height": height
            })
        
        db.commit()
        
        return {
            "generation_id": new_generation.id,
            "status": "completed",
            "message": f"재생성 완료! {len(results)}장의 썸네일이 생성되었습니다.",
            "images": saved_images
        }
        
    except Exception as e:
        print(f"재생성 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="재생성 중 오류가 발생했습니다."
        )