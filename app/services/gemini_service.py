import asyncio
import hashlib
from typing import List, Optional, Tuple
from pathlib import Path
import google.generativeai as genai
from PIL import Image as PILImage
from io import BytesIO
import base64

from app.config import get_settings
from app.services.cache_service import CacheService

settings = get_settings()


class GeminiService:
    """Gemini 2.5 Flash Image API 연동 서비스"""
    
    def __init__(self):
        # Gemini API 설정
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)
        self.cache_service = CacheService()
        
    async def generate_thumbnail(
        self,
        title: str,
        style_preset: str = "bold",
        reference_images: Optional[List[bytes]] = None,
        variants: int = 1
    ) -> List[Tuple[bytes, str]]:
        """
        썸네일 생성 메인 함수
        
        Args:
            title: 영상 제목 또는 스크립트
            style_preset: 스타일 프리셋 (bold, minimal, comic, tech)
            reference_images: 참고 이미지 리스트 (최대 3장)
            variants: 생성할 이미지 수 (1-3)
            
        Returns:
            List of (image_bytes, format) tuples
        """
        
        # 캐시 키 생성
        cache_key = self._generate_cache_key(title, style_preset, reference_images, variants)
        
        # 캐시 확인
        cached_result = await self.cache_service.get(cache_key)
        if cached_result:
            print(f"✅ 캐시에서 결과 반환: {cache_key[:16]}...")
            return cached_result
            
        # 프롬프트 생성
        prompt = self._build_prompt(title, style_preset, reference_images)
        
        print(f"🎨 Gemini API 호출 시작: {variants}장 생성")
        print(f"📝 프롬프트: {prompt[:100]}...")
        
        # Gemini API 호출
        results = []
        for i in range(variants):
            try:
                result = await self._call_gemini_api(prompt, reference_images)
                if result:
                    results.append(result)
                    print(f"✅ 이미지 {i+1}/{variants} 생성 완료")
                else:
                    print(f"❌ 이미지 {i+1}/{variants} 생성 실패")
                    
                # API 호출 간격 (Rate Limiting 방지)
                if i < variants - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                print(f"❌ Gemini API 호출 실패 ({i+1}/{variants}): {e}")
                continue
                
        # 결과 캐시 저장
        if results:
            await self.cache_service.set(cache_key, results)
            print(f"💾 결과 캐시 저장 완료: {len(results)}장")
            
        return results
        
    def _build_prompt(
        self, 
        title: str, 
        style_preset: str,
        reference_images: Optional[List[bytes]] = None
    ) -> str:
        """고급 프롬프트 빌드 - Gemini 2.5 Flash Image 최적화"""
        
        # 제목 요약 (2000자 → 200자)
        summarized_title = title[:200] if len(title) > 200 else title
        
        # 크기 최우선 강제 지시 (문서 베스트 프랙티스: "매우 구체적")
        size_enforcement = """CRITICAL: Generate image in exactly 1280x720 pixels (16:9 landscape aspect ratio). This is a mandatory YouTube thumbnail dimension. Do NOT create square or portrait images."""
        
        # 16:9 구도를 의식한 전문 프롬프트 (사용자 제안 반영)
        base_prompt = f"""{size_enforcement}

Create a professional YouTube thumbnail designed specifically for 16:9 aspect ratio (1280x720 final output).

COMPOSITION STRATEGY FOR 16:9:
- Left third: Safe zone for bold headline text "{summarized_title}"
- Right two-thirds: Main visual subject (portrait, object, or scene)
- Horizontal layout optimization: Wide landscape composition thinking
- Text-safe margins: Leave adequate breathing room on edges for mobile viewing

TITLE TO FEATURE: "{summarized_title}"

TECHNICAL SPECIFICATIONS:
- Target format: YouTube thumbnail 16:9 landscape orientation
- Final output: Will be processed to exactly 1280×720 pixels  
- Mobile optimization: Elements must remain clear at 120×68px preview size
- Platform requirements: Optimized for YouTube's thumbnail display system

PHOTOGRAPHY & VISUAL DIRECTION:
- Camera angle: Dynamic wide-angle perspective emphasizing horizontal composition
- Lighting: Professional studio lighting with strategic highlights and shadows
- Focus: Crystal-clear imagery with intentional depth of field for 16:9 framing
- Color grading: Vibrant, saturated colors optimized for small thumbnail preview
- Contrast: High contrast ratios for maximum visibility in YouTube's interface
- Depth: Foreground/background separation for visual hierarchy in wide format"""
        
        # 텍스트 렌더링 최적화 (Gemini의 강점 활용)
        text_optimization = """

TEXT RENDERING EXCELLENCE (Gemini Specialty):
- Typography: Bold, highly readable sans-serif fonts with perfect kerning
- Text placement: Strategically positioned for maximum impact and readability
- Text size: Large enough to be clearly readable even at small thumbnail sizes (120x68px preview)
- Text effects: Professional text treatments including shadows, outlines, or glows for visibility
- Text color: High contrast against background elements for perfect legibility
- Text hierarchy: Clear visual hierarchy with primary headline and optional secondary text"""
        
        # 스타일별 전문적 가이드라인 (대폭 강화)
        enhanced_style_guidelines = {
            "bold": """
BOLD STYLE EXECUTION:
- Visual impact: Explosive, high-energy composition with dramatic visual elements
- Color palette: Vibrant primary colors (electric blues, fiery reds, bright yellows) with strategic color blocking
- Lighting: Dramatic chiaroscuro lighting with strong directional shadows and bright highlights  
- Composition: Dynamic diagonal compositions, action-oriented poses, energetic movement
- Typography: Extra-bold, impactful fonts with strong presence and visual weight
- Elements: Power symbols, lightning bolts, burst effects, dynamic arrows, energetic patterns
- Mood: Excitement, urgency, power, confidence, breakthrough moments""",
            
            "minimal": """
MINIMAL STYLE EXECUTION:
- Visual philosophy: Less is more - strategic use of negative space and clean geometry
- Color palette: Sophisticated neutrals (whites, light grays, soft beiges) with single accent color
- Lighting: Soft, even lighting reminiscent of Scandinavian design photography
- Composition: Rule of thirds with intentional asymmetry and breathing room
- Typography: Clean, modern sans-serif fonts (Helvetica-style) with generous letter spacing
- Elements: Simple geometric shapes, subtle gradients, clean lines, minimal icons
- Mood: Calm, sophisticated, trustworthy, premium, professional clarity""",
            
            "comic": """
COMIC STYLE EXECUTION:
- Visual style: Vibrant cartoon illustration with bold outlines and flat color fills
- Color palette: Bright primary colors (comic book reds, blues, yellows) with high saturation
- Lighting: Stylized cartoon lighting with clear cel-shading and distinct highlight/shadow areas
- Composition: Dynamic action poses with exaggerated expressions and gestures  
- Typography: Playful, rounded fonts with comic book styling and speech bubble effects
- Elements: Cartoon burst effects, stars, exclamation marks, comic-style motion lines
- Mood: Fun, playful, energetic, approachable, entertaining, youthful excitement""",
            
            "tech": """
TECH STYLE EXECUTION:
- Visual aesthetic: Sleek, futuristic design with precision and digital sophistication
- Color palette: Cool technology colors (electric blues, digital teals, chrome silvers) with neon accents
- Lighting: Clean LED-style lighting with subtle lens flares and digital glow effects
- Composition: Geometric precision with grid-based layouts and technological patterns
- Typography: Modern, technical fonts with digital characteristics and sharp edges  
- Elements: Circuit patterns, holographic effects, digital grids, sleek interfaces, tech icons
- Mood: Innovation, precision, cutting-edge, professional, futuristic confidence"""
        }
        
        # 참고 이미지 처리 (향상된 지시사항)
        reference_instructions = ""
        if reference_images and len(reference_images) > 0:
            reference_instructions = f"""

REFERENCE IMAGE INTEGRATION ({len(reference_images)} images provided):
- Style Transfer: Extract and apply the overall aesthetic mood, color temperature, and visual treatment from the reference images
- Composition Inspiration: Use the reference images' layout principles and element positioning as creative guidance  
- Color Harmony: Adopt the reference images' color palette while enhancing it for YouTube thumbnail optimization
- Visual Consistency: Maintain the artistic direction established by the reference images while optimizing for engagement
- Creative Fusion: Seamlessly blend the reference aesthetic with the selected "{style_preset}" style preset"""
        
        # YouTube 최적화 전략
        youtube_optimization = """

YOUTUBE THUMBNAIL OPTIMIZATION STRATEGY:
- Click-through Psychology: Design elements that create curiosity, urgency, or emotional response
- Mobile Optimization: Ensure all elements remain clear and impactful on mobile devices
- Competition Awareness: Stand out from typical YouTube thumbnail designs in the same category  
- Engagement Triggers: Visual elements that encourage clicks (arrows, highlights, intriguing visuals)
- Brand Consistency: Professional appearance that builds trust and authority
- Thumbnail Performance: Optimized for YouTube's algorithm and user browsing patterns"""
        
        # 최종 품질 보장
        quality_assurance = f"""

FINAL QUALITY REQUIREMENTS:
- Dimension Verification: Confirm final output is EXACTLY 1280x720 pixels in landscape format
- Text Readability Test: All text must be perfectly readable even when scaled down to 120x68 pixels
- Visual Impact Assessment: Image must create immediate visual impact within 0.5 seconds of viewing
- Style Consistency: Perfect execution of "{style_preset}" style with professional quality standards
- Technical Excellence: No pixelation, artifacts, or compression issues in the final output"""
        
        # 전체 프롬프트 조합
        complete_prompt = (
            base_prompt + 
            text_optimization + 
            enhanced_style_guidelines.get(style_preset, "") +
            reference_instructions +
            youtube_optimization +
            quality_assurance
        )
            
        return complete_prompt.strip()
        
    async def _call_gemini_api(
        self, 
        prompt: str, 
        reference_images: Optional[List[bytes]] = None
    ) -> Optional[Tuple[bytes, str]]:
        """Gemini API 실제 호출 및 후처리"""
        
        try:
            # 컨텐츠 구성
            contents = [prompt]
            
            # 참고 이미지 추가
            if reference_images:
                for img_bytes in reference_images:
                    try:
                        # PIL Image로 변환하여 검증
                        img = PILImage.open(BytesIO(img_bytes))
                        img.verify()  # 이미지 유효성 검증
                        
                        # 다시 열어서 사용 (verify 후에는 재사용 불가)
                        img = PILImage.open(BytesIO(img_bytes))
                        contents.append(img)
                    except Exception as e:
                        print(f"⚠️ 참고 이미지 처리 오류: {e}")
                        continue
                    
            print(f"📡 Gemini API 호출 중... (컨텐츠: {len(contents)}개)")
                    
            # API 호출 (동기 함수를 비동기로 실행)
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content(contents)
            )
            
            # 응답에서 이미지 추출
            if response.candidates and len(response.candidates) > 0:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        mime_type = part.inline_data.mime_type
                        
                        # MIME 타입에서 형식 추출
                        format_map = {
                            'image/png': 'png',
                            'image/jpeg': 'jpg',
                            'image/jpg': 'jpg',
                            'image/gif': 'gif'
                        }
                        image_format = format_map.get(mime_type, 'png')
                        
                        # 유튜브 썸네일 크기로 후처리
                        processed_image_data = await self._process_to_youtube_size(image_data)
                        
                        return (processed_image_data, image_format)
                        
            print("❌ API 응답에 이미지가 없음")
            return None
                        
        except Exception as e:
            print(f"❌ Gemini API 호출 중 오류: {e}")
            raise
            
    async def _process_to_youtube_size(self, image_data: bytes) -> bytes:
        """이미지를 유튜브 썸네일 크기(1280x720)로 후처리"""
        
        try:
            # PIL로 이미지 열기
            img = PILImage.open(BytesIO(image_data))
            original_size = img.size
            print(f"🖼️ 원본 이미지 크기: {original_size[0]}x{original_size[1]}")
            
            # 목표 크기 설정
            target_width, target_height = 1280, 720
            target_ratio = target_width / target_height  # 16:9 = 1.777...
            
            # 현재 이미지 비율 계산
            current_ratio = img.width / img.height
            
            # 비율에 따라 크롭 또는 리사이즈 결정
            if abs(current_ratio - target_ratio) < 0.1:
                # 비율이 거의 맞는 경우: 직접 리사이즈
                processed_img = img.resize((target_width, target_height), PILImage.LANCZOS)
                print(f"📐 직접 리사이즈: {original_size} → 1280x720")
            else:
                # 비율이 다른 경우: 스마트 크롭 + 리사이즈
                if current_ratio > target_ratio:
                    # 너무 넓은 경우: 좌우 크롭
                    new_width = int(img.height * target_ratio)
                    left = (img.width - new_width) // 2
                    crop_box = (left, 0, left + new_width, img.height)
                    print(f"📐 가로 크롭: {original_size} → {new_width}x{img.height}")
                else:
                    # 너무 높은 경우: 상하 크롭
                    new_height = int(img.width / target_ratio)
                    top = (img.height - new_height) // 2
                    crop_box = (0, top, img.width, top + new_height)
                    print(f"📐 세로 크롭: {original_size} → {img.width}x{new_height}")
                
                cropped_img = img.crop(crop_box)
                processed_img = cropped_img.resize((target_width, target_height), PILImage.LANCZOS)
                
            print(f"✅ 최종 크기: {processed_img.size[0]}x{processed_img.size[1]}")
            
            # 처리된 이미지를 bytes로 변환
            output_buffer = BytesIO()
            processed_img.save(output_buffer, format='PNG', optimize=True, quality=95)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            print(f"❌ 이미지 후처리 실패: {e}")
            # 실패 시 원본 반환
            return image_data
            
    def _generate_cache_key(
        self, 
        title: str, 
        style_preset: str,
        reference_images: Optional[List[bytes]] = None,
        variants: int = 1
    ) -> str:
        """캐시 키 생성"""
        
        # 제목 요약
        summarized_title = title[:200] if len(title) > 200 else title
        
        key_parts = [
            summarized_title,
            style_preset,
            str(variants)
        ]
        
        # 참고 이미지 해시 추가
        if reference_images:
            img_hashes = []
            for img_bytes in reference_images:
                img_hash = hashlib.md5(img_bytes).hexdigest()[:8]
                img_hashes.append(img_hash)
            key_parts.extend(img_hashes)
            
        # 최종 키 생성
        key_string = "|".join(key_parts)
        cache_key = hashlib.sha256(key_string.encode()).hexdigest()
        
        return cache_key
        
    async def get_api_usage_info(self) -> dict:
        """API 사용량 정보 (모의)"""
        # 실제로는 Google API 콘솔에서 확인해야 함
        return {
            "daily_limit": 100,
            "used_today": 0,  # 실제 구현 시 DB에서 조회
            "remaining": 100,
            "reset_time": "2025-09-07T00:00:00Z"
        }
        
    async def health_check(self) -> bool:
        """Gemini API 연결 상태 확인"""
        try:
            # 간단한 텍스트 생성으로 API 상태 확인
            test_response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.model.generate_content("Hello")
            )
            return True
        except Exception as e:
            print(f"❌ Gemini API 헬스체크 실패: {e}")
            return False