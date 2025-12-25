"""
Roast My Resume API routes - viral growth feature.
Free tier endpoint (no auth required, rate-limited by IP).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..services.ai_service import AIService
from ..utils.security import validate_cv_text
from ..utils.debug import print_step
import hashlib
import time
import re

router = APIRouter(prefix="/roast", tags=["roast"])

# In-memory rate limiter (simple MVP; use Redis for production)
roast_cache: dict[str, float] = {}

class RoastRequest(BaseModel):
    cv_text: str = Field(..., min_length=100, max_length=10000, description="CV text to roast")

class RoastResponse(BaseModel):
    roast: str = Field(..., description="The roast feedback")
    score: int = Field(..., ge=0, le=10, description="Roast score out of 10")
    share_url: str = Field(..., description="URL for sharing the roast with OG image")

@router.post("", response_model=RoastResponse)
async def roast_cv(request: RoastRequest):
    """
    Generate a brutally honest AI roast of a CV.
    
    Free tier endpoint (no auth required, rate-limited by IP/content hash).
    Returns entertaining, constructive feedback optimized for viral sharing.
    """
    print_step("Roast Request Received", {
        "cv_text_length": len(request.cv_text)
    }, "input")
    
    # Validate input
    try:
        validated_text = validate_cv_text(request.cv_text)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CV text: {str(e)}"
        )
    
    # Rate limiting (prevent abuse)
    # Use content hash to prevent same CV from being roasted repeatedly
    content_hash = hashlib.md5(validated_text[:500].encode()).hexdigest()
    
    if content_hash in roast_cache:
        last_roast_time = roast_cache[content_hash]
        cooldown_seconds = 300  # 5 minutes
        time_remaining = cooldown_seconds - (time.time() - last_roast_time)
        
        if time_remaining > 0:
            raise HTTPException(
                status_code=429,
                detail=f"Slow down! You can only roast once every 5 minutes. Try again in {int(time_remaining)} seconds."
            )
    
    # Generate roast using AI service
    # Use system OpenAI key (free tier feature)
    try:
        ai_service = AIService(provider="openai", api_key=None)
    except ValueError as e:
        # System OpenAI key not configured
        raise HTTPException(
            status_code=503,
            detail="Roast service is temporarily unavailable. Please try again later."
        )
    
    system_prompt = "You are a brutally honest career coach with a sharp sense of humor and genuine desire to help people improve their CVs."
    
    user_prompt = f"""You are a brutally honest career coach. A user has submitted their CV for a "roast" – your job is to provide honest, constructive feedback in an entertaining way.

Rules:
- Be witty but not cruel
- Point out 3-5 specific issues (typos, vague bullet points, poor formatting, buzzwords, lack of quantification)
- Provide 1-2 actionable fixes
- Start with a "ROAST SCORE: X/10" (lower = more issues, higher = better CV)
- Keep it under 200 words
- Use emojis sparingly (only fire emoji for score)

CV Text:
{validated_text[:2000]}

Generate the roast:"""
    
    try:
        llm = ai_service._get_llm_client()
        roast_text = await llm.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=300,
            temperature=0.8  # Higher creativity for entertaining roasts
        )
        
        print_step("Roast Generated", {
            "roast_length": len(roast_text)
        }, "output")
        
        # Extract score from roast (simple regex)
        score_match = re.search(r'(\d+)/10', roast_text)
        score = int(score_match.group(1)) if score_match else 5
        
        # Ensure score is in valid range
        score = max(0, min(10, score))
        
        # Update rate limiter
        roast_cache[content_hash] = time.time()
        
        # Generate share URL (for OG image)
        share_id = hashlib.md5(roast_text.encode()).hexdigest()[:8]
        
        # Extract a highlight (first sentence after score, or first 150 chars)
        lines = roast_text.split('\n')
        highlight = ""
        for line in lines:
            if line.strip() and 'ROAST SCORE' not in line.upper():
                highlight = line.strip()
                break
        
        if not highlight:
            highlight = roast_text[:150]
        
        # Build share URL with score and highlight as query params
        # Frontend will use this to fetch OG image
        from urllib.parse import urlencode
        share_params = urlencode({
            'id': share_id,
            'score': score,
            'highlight': highlight[:200]  # Limit length for URL safety
        })
        share_url = f"/roast/share?{share_params}"
        
        print_step("Roast Complete", {
            "score": score,
            "share_id": share_id
        }, "output")
        
        return RoastResponse(
            roast=roast_text,
            score=score,
            share_url=share_url
        )
    
    except Exception as e:
        print_step("Roast Generation Error", str(e), "error")
        raise HTTPException(
            status_code=500,
            detail="Roast generation failed. Our AI is having a bad day. Please try again."
        )


