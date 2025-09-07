from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from PIL import Image, ImageEnhance
import uuid

from app.database import get_db
from app.models.generation import Image as ImageModel
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/{image_id}/download")
async def download_image(
    image_id: int,
    db: Session = Depends(get_db)
):
    """이미지 다운로드 API"""
    
    image_record = db.query(ImageModel).filter(ImageModel.id == image_id).first()
    
    if not image_record:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    
    # 가장 최신 처리된 이미지 경로 선택
    image_path = None
    if image_record.resized_path:
        image_path = image_record.resized_path
    elif image_record.filtered_path:
        image_path = image_record.filtered_path
    else:
        image_path = image_record.original_path
    
    file_path = Path(image_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="이미지 파일을 찾을 수 없습니다.")
    
    # 파일명 생성
    filename = f"thumbanana_thumbnail_{image_id}.{image_record.format}"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=f"image/{image_record.format}"
    )


@router.post("/{image_id}/filter")
async def apply_filter(
    image_id: int,
    brightness: int = 0,    # -2 ~ +2
    contrast: int = 0,      # -2 ~ +2
    sharpness: int = 0,     # -2 ~ +2
    saturation: int = 0,    # -2 ~ +2
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # TODO: 인증 구현 후
):
    """이미지 필터 적용 API (로그인 사용자 전용)"""
    
    # TODO: 로그인 사용자 검증
    # if not current_user:
    #     raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    image_record = db.query(ImageModel).filter(ImageModel.id == image_id).first()
    
    if not image_record:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    
    # 입력값 검증
    for value, name in [(brightness, "brightness"), (contrast, "contrast"), 
                        (sharpness, "sharpness"), (saturation, "saturation")]:
        if not -2 <= value <= 2:
            raise HTTPException(status_code=400, detail=f"{name} 값은 -2에서 2 사이여야 합니다.")
    
    try:
        # 원본 이미지 로드
        source_path = image_record.resized_path if image_record.resized_path else image_record.original_path
        with Image.open(source_path) as img:
            # 필터 적용
            if brightness != 0:
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.0 + (brightness * 0.3))  # -0.6 ~ +0.6
            
            if contrast != 0:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.0 + (contrast * 0.3))  # -0.6 ~ +0.6
            
            if sharpness != 0:
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.0 + (sharpness * 0.5))  # -1.0 ~ +1.0
            
            if saturation != 0:
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(1.0 + (saturation * 0.4))  # -0.8 ~ +0.8
            
            # 필터 적용된 이미지 저장
            filter_id = str(uuid.uuid4())
            filtered_path = Path(settings.generated_dir) / "filtered" / f"{filter_id}.{image_record.format}"
            filtered_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 이미지 저장
            if image_record.format.lower() == 'jpg':
                img.save(filtered_path, format='JPEG', quality=90, optimize=True)
            else:
                img.save(filtered_path, format=image_record.format.upper(), optimize=True)
            
            # 데이터베이스 업데이트
            image_record.filtered_path = str(filtered_path)
            db.commit()
        
        return {
            "status": "success",
            "message": "필터가 성공적으로 적용되었습니다.",
            "image_id": image_id,
            "download_url": f"/api/images/{image_id}/download",
            "applied_filters": {
                "brightness": brightness,
                "contrast": contrast,
                "sharpness": sharpness,
                "saturation": saturation
            }
        }
        
    except Exception as e:
        print(f"❌ 필터 적용 실패: {e}")
        raise HTTPException(status_code=500, detail="필터 적용 중 오류가 발생했습니다.")


@router.post("/{image_id}/resize")
async def resize_image(
    image_id: int,
    target_size: str = "1280x720",
    method: str = "center_crop",  # center_crop 또는 canvas_extend
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # TODO: 인증 구현 후
):
    """이미지 리사이즈 API (로그인 사용자 전용)"""
    
    # TODO: 로그인 사용자 검증
    # if not current_user:
    #     raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    image_record = db.query(ImageModel).filter(ImageModel.id == image_id).first()
    
    if not image_record:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    
    # 타겟 크기 파싱
    try:
        target_width, target_height = map(int, target_size.split('x'))
    except ValueError:
        raise HTTPException(status_code=400, detail="올바른 크기 형식을 입력하세요 (예: 1280x720)")
    
    # 메소드 검증
    if method not in ["center_crop", "canvas_extend"]:
        raise HTTPException(status_code=400, detail="지원하지 않는 리사이즈 방법입니다.")
    
    try:
        # 소스 이미지 경로 결정
        source_path = image_record.filtered_path if image_record.filtered_path else image_record.original_path
        
        with Image.open(source_path) as img:
            original_width, original_height = img.size
            target_ratio = target_width / target_height
            original_ratio = original_width / original_height
            
            if method == "center_crop":
                # 가운데 크롭
                if original_ratio > target_ratio:
                    # 원본이 더 넓음 - 높이 기준으로 크롭
                    new_height = original_height
                    new_width = int(original_height * target_ratio)
                    left = (original_width - new_width) // 2
                    img = img.crop((left, 0, left + new_width, new_height))
                else:
                    # 원본이 더 높음 - 너비 기준으로 크롭
                    new_width = original_width
                    new_height = int(original_width / target_ratio)
                    top = (original_height - new_height) // 2
                    img = img.crop((0, top, new_width, top + new_height))
                
                # 타겟 사이즈로 리사이즈
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
            elif method == "canvas_extend":
                # 캔버스 확장 (비율 유지하며 패딩)
                img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
                
                # 새 캔버스 생성 (흰색 배경)
                new_img = Image.new('RGB', (target_width, target_height), 'white')
                
                # 중앙에 이미지 배치
                paste_x = (target_width - img.width) // 2
                paste_y = (target_height - img.height) // 2
                new_img.paste(img, (paste_x, paste_y))
                
                img = new_img
            
            # 리사이즈된 이미지 저장
            resize_id = str(uuid.uuid4())
            resized_path = Path(settings.generated_dir) / "resized" / f"{resize_id}.{image_record.format}"
            resized_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 이미지 저장
            if image_record.format.lower() == 'jpg':
                img.save(resized_path, format='JPEG', quality=95, optimize=True)
            else:
                img.save(resized_path, format=image_record.format.upper(), optimize=True)
            
            # 데이터베이스 업데이트
            image_record.resized_path = str(resized_path)
            db.commit()
        
        return {
            "status": "success",
            "message": f"이미지가 {target_size}로 성공적으로 리사이즈되었습니다.",
            "image_id": image_id,
            "download_url": f"/api/images/{image_id}/download",
            "original_size": f"{original_width}x{original_height}",
            "new_size": f"{target_width}x{target_height}",
            "method": method
        }
        
    except Exception as e:
        print(f"❌ 리사이즈 실패: {e}")
        raise HTTPException(status_code=500, detail="이미지 리사이즈 중 오류가 발생했습니다.")


@router.get("/{image_id}/info")
async def get_image_info(
    image_id: int,
    db: Session = Depends(get_db)
):
    """이미지 정보 조회 API"""
    
    image_record = db.query(ImageModel).filter(ImageModel.id == image_id).first()
    
    if not image_record:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    
    return {
        "id": image_record.id,
        "generation_id": image_record.generation_id,
        "format": image_record.format,
        "width": image_record.width,
        "height": image_record.height,
        "created_at": image_record.created_at.isoformat(),
        "has_filter_applied": image_record.filtered_path is not None,
        "is_resized": image_record.resized_path is not None,
        "download_url": f"/api/images/{image_id}/download"
    }