"""
LLM provider factory for BYOK (Bring Your Own Key) support.
Handles OpenAI and Gemini AI Studio API clients.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx
from openai import OpenAI

from ..core.config import settings
from ..utils.debug import print_step


class LLMProvider:
    """Abstract base for LLM provider clients."""
    
    async def chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """Generate a chat completion response."""
        raise NotImplementedError
    
    async def stream_chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ):
        """Stream a chat completion response (yields chunks)."""
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """OpenAI API provider using official SDK."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.default_model = model
    
    async def chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """Generate a chat completion using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            # Never log the API key in error messages
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def stream_chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ):
        """Stream a chat completion using OpenAI API."""
        try:
            stream = self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            # Never log the API key in error messages
            raise Exception(f"OpenAI API streaming error: {str(e)}")


class GeminiProvider(LLMProvider):
    """Gemini AI Studio API provider using REST API."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.default_model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    async def chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """Generate a chat completion using Gemini AI Studio API."""
        model_name = model or self.default_model
        url = f"{self.base_url}/models/{model_name}:generateContent"
        
        # Gemini API request format
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url,
                    params={"key": self.api_key},
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    error_detail = response.text[:200] if response.text else "Unknown error"
                    raise Exception(f"Gemini API error (status {response.status_code}): {error_detail}")
                
                data = response.json()
                
                # Parse Gemini response structure
                candidates = data.get("candidates", [])
                if not candidates:
                    raise Exception("Gemini API returned no candidates")
                
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    raise Exception("Gemini API returned no content parts")
                
                # Concatenate all text parts
                text_parts = [part.get("text", "") for part in parts]
                return "".join(text_parts)
                
        except httpx.TimeoutException:
            raise Exception("Gemini API request timed out")
        except httpx.RequestError as e:
            raise Exception(f"Gemini API request failed: {str(e)}")
        except Exception as e:
            # Never log the API key
            raise Exception(f"Gemini API error: {str(e)}")
    
    async def stream_chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ):
        """
        Stream a chat completion using Gemini AI Studio API.
        
        Note: Gemini API doesn't support true streaming in the same way as OpenAI.
        This implementation generates the full response and yields it word by word.
        """
        try:
            # Generate full response first
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
                # Small delay to simulate streaming
                import asyncio
                await asyncio.sleep(0.03)
        except Exception as e:
            # Never log the API key
            raise Exception(f"Gemini API streaming error: {str(e)}")


def create_llm_provider(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> LLMProvider:
    """
    Factory function to create an LLM provider client.
    
    Args:
        provider: Provider name ('openai' or 'gemini')
        api_key: User's API key (if None, uses system OPENAI_API_KEY for OpenAI)
        model: Optional model override
        
    Returns:
        LLMProvider instance
        
    Raises:
        ValueError: If provider is unsupported or configuration is invalid
    """
    provider = provider.lower()
    
    if provider == "openai":
        resolved_key = api_key or settings.OPENAI_API_KEY
        if not resolved_key:
            raise ValueError(
                "OpenAI API key is required. Either provide X-User-Api-Key header "
                "or configure OPENAI_API_KEY environment variable."
            )
        
        print_step("LLM Provider", {
            "provider": "openai",
            "key_source": "user" if api_key else "system",
            "model": model or "gpt-4"
        }, "info")
        
        return OpenAIProvider(api_key=resolved_key, model=model or "gpt-4")
    
    elif provider == "gemini":
        if not api_key:
            raise ValueError(
                "Gemini requires user-provided API key via X-User-Api-Key header. "
                "System fallback is not available for Gemini."
            )
        
        print_step("LLM Provider", {
            "provider": "gemini",
            "key_source": "user",
            "model": model or "gemini-1.5-flash"
        }, "info")
        
        return GeminiProvider(api_key=api_key, model=model or "gemini-1.5-flash")
    
    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported: openai, gemini")


