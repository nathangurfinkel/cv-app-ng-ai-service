"""
Interview Routes - Voice Mock Interviewer

Provides real-time interview simulation with streaming LLM responses.
Uses Server-Sent Events (SSE) for low-latency conversation flow.
"""

from fastapi import APIRouter, Request, Header, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import json
import time
import logging

from app.services.ai_service import AIService
from app.utils.security import validate_cv_text, validate_job_description
from app.utils.tier_validation import require_mock_interviewer, UserTier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/interview", tags=["interview"])

# Difficulty-based interview strategies
DIFFICULTY_STRATEGIES = {
    'easy': {
        'opening': 'Ask warm, friendly opening questions. Keep it conversational and supportive. Avoid follow-ups that drill too deep.',
        'followup': 'Ask gentle follow-up questions. If the candidate struggles, move on gracefully. Keep questions encouraging and straightforward.'
    },
    'medium': {
        'opening': 'Ask standard behavioral interview questions. Be professional but approachable.',
        'followup': 'Probe for specifics with follow-up questions like "Can you give an example?" or "What was the outcome?" Ask about the candidate\'s role and contributions.'
    },
    'hard': {
        'opening': 'Ask challenging behavioral and situational questions. Expect detailed, structured answers.',
        'followup': 'Ask probing follow-ups that test depth: "What would you do differently?" "How did you measure success?" "What was the biggest challenge?" Dig into decision-making processes and trade-offs.'
    }
}


class InterviewStartRequest(BaseModel):
    cv_summary: str = Field(..., max_length=1000, description="Brief CV summary for context")
    job_title: str = Field(..., max_length=200, description="Target job title")
    difficulty: str = Field(default="medium", description="easy, medium, hard")


class InterviewAnswerRequest(BaseModel):
    session_id: str = Field(..., description="Interview session ID")
    question: str = Field(..., max_length=500, description="The question that was asked")
    answer: str = Field(..., max_length=2000, description="User's answer")


class InterviewAnalysisRequest(BaseModel):
    transcript: str = Field(..., max_length=10000, description="Full interview transcript")
    duration_seconds: int = Field(..., gt=0, description="Interview duration in seconds")


@router.post("/start")
async def start_interview(
    request: InterviewStartRequest,
    x_user_tier: Optional[str] = Header(None, alias="X-User-Tier"),
    x_user_provider: Optional[str] = Header(None, alias="X-User-Provider"),
    x_user_api_key: Optional[str] = Header(None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_mock_interviewer),
):
    """
    Start a new interview session and return the first question.
    
    Returns:
        - session_id: Unique identifier for this interview
        - question: The first interview question
    """
    
    cv_summary = validate_cv_text(request.cv_summary)
    job_title = validate_job_description(request.job_title)
    
    if request.difficulty not in ['easy', 'medium', 'hard']:
        request.difficulty = 'medium'
    
    session_id = f"interview_{int(time.time() * 1000)}"
    
    difficulty_strategy = DIFFICULTY_STRATEGIES[request.difficulty]
    
    prompt = f"""You are a hiring manager interviewing a candidate for a {job_title} position.

Candidate Summary: {cv_summary}

Interview Difficulty: {request.difficulty.upper()}
Strategy: {difficulty_strategy['opening']}

Ask an engaging opening question (e.g., "Tell me about yourself and why you're interested in this role").
Keep it conversational and natural. Do not include any preamble, just the question."""
    
    try:
        # Create AIService with correct constructor signature
        provider = x_user_provider or "openai"
        ai_service = AIService(provider=provider, api_key=x_user_api_key)
        
        first_question = await ai_service.generate_completion(
            prompt=prompt,
            max_tokens=100,
            temperature=0.8
        )
        
        logger.info(f"[Interview] Started session {session_id} for job: {job_title}")
        
        return {
            "session_id": session_id,
            "question": first_question.strip()
        }
    
    except Exception as e:
        logger.error(f"[Interview] Error starting session: {e}")
        raise


@router.get("/answer")
async def handle_answer(
    session_id: str,
    question: str,
    answer: str,
    difficulty: str = 'medium',
    x_user_tier: Optional[str] = Header(None, alias="X-User-Tier"),
    x_user_provider: Optional[str] = Header(None, alias="X-User-Provider"),
    x_user_api_key: Optional[str] = Header(None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_mock_interviewer),
):
    """
    Process user's answer and stream the next question via SSE.
    
    Query Parameters:
        - session_id: Interview session ID
        - question: The previous question
        - answer: User's answer
        - difficulty: Interview difficulty (easy, medium, hard)
    
    Returns:
        Server-Sent Events stream with LLM tokens
    """
    
    answer_text = validate_cv_text(answer)
    
    # Validate difficulty
    if difficulty not in ['easy', 'medium', 'hard']:
        difficulty = 'medium'
    
    difficulty_strategy = DIFFICULTY_STRATEGIES[difficulty]
    
    async def generate_sse():
        prompt = f"""You are a hiring manager conducting a {difficulty.upper()} difficulty interview.

Strategy: {difficulty_strategy['followup']}

Previous Question: {question}
Candidate's Answer: {answer_text}

Generate a natural follow-up question based on their answer. Do not include any preamble, just the question."""
        
        try:
            # Create AIService with correct constructor signature
            provider = x_user_provider or "openai"
            ai_service = AIService(provider=provider, api_key=x_user_api_key)
            
            async for chunk in ai_service.stream_completion(
                prompt=prompt,
                max_tokens=150,
                temperature=0.9
            ):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            logger.error(f"[Interview] Error streaming response: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/analyze")
async def analyze_interview(
    request: InterviewAnalysisRequest,
    x_user_tier: Optional[str] = Header(None, alias="X-User-Tier"),
    x_user_provider: Optional[str] = Header(None, alias="X-User-Provider"),
    x_user_api_key: Optional[str] = Header(None, alias="X-User-Api-Key"),
    tier: UserTier = Depends(require_mock_interviewer),
):
    """
    Analyze interview transcript and provide feedback.
    
    Note: Currently the frontend performs this analysis locally using
    regex-based heuristics. This endpoint is provided for future enhancement
    with LLM-based analysis.
    
    Returns:
        - filler_word_count: Number of filler words detected
        - words_per_minute: Speaking pace
        - confidence_score: 0-100 confidence rating
        - suggestions: List of improvement suggestions
    """
    
    transcript_text = validate_cv_text(request.transcript)
    
    prompt = f"""Analyze this interview transcript and provide constructive feedback.

Transcript: {transcript_text}
Duration: {request.duration_seconds} seconds

Provide:
1. Key strengths in the candidate's communication
2. Areas for improvement
3. Specific actionable suggestions

Keep feedback supportive and constructive. Format as JSON with keys: strengths, improvements, suggestions."""
    
    try:
        # Create AIService with correct constructor signature
        provider = x_user_provider or "openai"
        ai_service = AIService(provider=provider, api_key=x_user_api_key)
        
        analysis = await ai_service.generate_completion(
            prompt=prompt,
            max_tokens=500,
            temperature=0.7
        )
        
        # Calculate basic metrics from transcript
        words = transcript_text.split()
        word_count = len(words)
        duration_minutes = request.duration_seconds / 60.0
        words_per_minute = int(word_count / duration_minutes) if duration_minutes > 0 else 0
        
        # Count filler words (simple heuristic)
        filler_words = ['um', 'uh', 'like', 'you know', 'so', 'well', 'actually', 'basically']
        filler_word_count = sum(1 for word in words if word.lower() in filler_words)
        
        # Parse AI feedback
        try:
            feedback = json.loads(analysis)
            suggestions = feedback.get("suggestions", [])
            if isinstance(suggestions, str):
                suggestions = [suggestions]
        except:
            # If analysis is not JSON, use it as a single suggestion
            suggestions = [analysis] if analysis else []
        
        # Calculate confidence score (0-100) based on filler words and speaking pace
        # Lower filler words and moderate pace = higher confidence
        filler_penalty = min(filler_word_count * 5, 50)  # Max 50 point penalty
        pace_score = 50  # Default, could be enhanced with actual pace analysis
        confidence_score = max(0, min(100, 100 - filler_penalty + (pace_score - 50)))
        
        return {
            "filler_word_count": filler_word_count,
            "words_per_minute": words_per_minute,
            "confidence_score": confidence_score,
            "suggestions": suggestions
        }
    
    except Exception as e:
        logger.error(f"[Interview] Error analyzing transcript: {e}")
        raise

