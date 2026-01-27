"""
Mock LLM provider for testing without real API calls.
Returns predictable responses based on prompt content.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.services.llm_factory import LLMProvider


class MockLLMProvider(LLMProvider):
    """Mock LLM provider that returns predictable responses."""
    
    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """
        Initialize mock LLM provider.
        
        Args:
            responses: Optional custom responses dict. If None, uses default responses.
        """
        self.responses = responses or {}
        self._call_count = 0
    
    async def chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """Generate a mock chat completion response."""
        self._call_count += 1
        
        # Check for custom response first
        prompt_key = f"{system_prompt[:50]}_{user_prompt[:50]}"
        if prompt_key in self.responses:
            return self.responses[prompt_key]
        
        # Determine response type based on prompt content
        user_prompt_lower = user_prompt.lower()
        
        if "extract" in user_prompt_lower or "extract structured data" in user_prompt_lower:
            return self._mock_extract_response()
        elif "tailor" in user_prompt_lower or "improve and tailor" in user_prompt_lower:
            return self._mock_tailor_response()
        elif "evaluate" in user_prompt_lower or "committee" in user_prompt_lower:
            return self._mock_evaluate_response()
        elif "rephrase" in user_prompt_lower or "improve clarity" in user_prompt_lower:
            return self._mock_rephrase_response()
        elif "recommend" in user_prompt_lower or "template format" in user_prompt_lower:
            return self._mock_recommend_response()
        elif "inject" in user_prompt_lower and "keyword" in user_prompt_lower:
            return self._mock_inject_keyword_response()
        elif "elaborate" in user_prompt_lower or "user context" in user_prompt_lower:
            return self._mock_elaborate_response()
        elif "summarize" in user_prompt_lower or "requirements" in user_prompt_lower:
            return self._mock_summarize_response()
        else:
            # Default response
            return json.dumps({"message": "Mock response"})
    
    async def stream_chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ):
        """Stream a mock chat completion response."""
        # Generate full response
        full_response = await self.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        # Yield word by word to simulate streaming
        words = full_response.split()
        for word in words:
            yield word + " "
    
    def _mock_extract_response(self) -> str:
        """Mock response for CV extraction."""
        return json.dumps({
            "personal": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1-555-0123",
                "location": "San Francisco, CA",
                "website": "johndoe.com",
                "linkedin": "linkedin.com/in/johndoe",
                "github": "github.com/johndoe"
            },
            "professional_summary": "Experienced software engineer with 5+ years in backend development.",
            "experience": [
                {
                    "role": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "startDate": "Jan 2020",
                    "endDate": "Present",
                    "location": "San Francisco, CA",
                    "description": "Led development of microservices architecture",
                    "achievements": [
                        "Improved system performance by 40%",
                        "Mentored team of 5 junior developers"
                    ]
                }
            ],
            "education": [
                {
                    "degree": "Bachelor of Science",
                    "institution": "University of California",
                    "field": "Computer Science",
                    "startDate": "2014",
                    "endDate": "2018",
                    "gpa": "3.8"
                }
            ],
            "projects": [
                {
                    "name": "E-commerce Platform",
                    "description": "Built scalable e-commerce platform using microservices",
                    "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
                    "link": "https://github.com/johndoe/ecommerce"
                }
            ],
            "skills": {
                "technical": ["Python", "FastAPI", "PostgreSQL", "Docker"],
                "soft": ["Leadership", "Communication"],
                "languages": ["English", "Spanish"]
            },
            "licenses_certifications": [],
            "target_job": {
                "title": "",
                "company": ""
            }
        })
    
    def _mock_tailor_response(self) -> str:
        """Mock response for CV tailoring (same structure as extract)."""
        return self._mock_extract_response()
    
    def _mock_evaluate_response(self) -> str:
        """Mock response for committee evaluation."""
        return json.dumps({
            "recruiter": {
                "score": 8,
                "strengths": ["Strong technical skills", "Relevant experience"],
                "improvements": ["Could highlight more leadership examples"],
                "reasoning": "Candidate has solid technical background matching job requirements."
            },
            "hr": {
                "score": 7,
                "strengths": ["Clear communication", "Professional presentation"],
                "improvements": ["Could add more soft skills"],
                "reasoning": "CV is well-structured and professional."
            },
            "manager": {
                "score": 9,
                "strengths": ["Excellent technical match", "Proven track record"],
                "improvements": ["Could emphasize impact metrics more"],
                "reasoning": "Strong candidate with relevant experience and achievements."
            }
        })
    
    def _mock_rephrase_response(self) -> str:
        """Mock response for rephrasing."""
        return "Led development of scalable microservices architecture, improving system performance by 40% and mentoring a team of 5 junior developers."
    
    def _mock_recommend_response(self) -> str:
        """Mock response for template recommendation."""
        return json.dumps({
            "recommended_template": "reverse-chronological",
            "confidence_score": 85,
            "reasoning": "Candidate has strong linear career progression with clear advancement.",
            "format_explanation": "Reverse-chronological format highlights recent experience and career growth.",
            "alternatives": [
                {
                    "template": "combination",
                    "reason": "Could also work well to emphasize technical skills upfront"
                }
            ]
        })
    
    def _mock_inject_keyword_response(self) -> str:
        """Mock response for keyword injection."""
        # Return successful injection (not REQUIRES_CONTEXT)
        return "Led development of scalable microservices architecture using CI/CD, improving system performance by 40%."
    
    def _mock_elaborate_response(self) -> str:
        """Mock response for elaboration with keyword."""
        return "Led development of scalable microservices architecture using CI/CD pipelines, improving system performance by 40% and reducing deployment time by 50%."
    
    def _mock_summarize_response(self) -> str:
        """Mock response for job description summarization."""
        return """Technical Requirements:
1. Microservices architecture
2. Python and FastAPI
3. Team leadership
4. Performance optimization
5. CI/CD pipelines

Soft Skills:
1. Communication
2. Problem-solving
3. Collaboration"""

