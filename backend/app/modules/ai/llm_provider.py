from typing import Dict, Any, Optional
import json
import httpx
from app.config import settings


class LLMProvider:
    def generate_json(self, system: str, user: str, timeout: float = 12.0) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class FakeLLMProvider(LLMProvider):
    def __init__(self, response: Optional[Dict[str, Any]] = None, raise_error: bool = False):
        self.response = response
        self.raise_error = raise_error

    def generate_json(self, system: str, user: str, timeout: float = 12.0) -> Optional[Dict[str, Any]]:
        if self.raise_error:
            raise TimeoutError("Simulated LLM timeout")
        return self.response


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model

    def generate_json(self, system: str, user: str, timeout: float = 12.0) -> Optional[Dict[str, Any]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
        }
        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text)
        except Exception:
            return None
        return None


def get_llm_provider() -> Optional[LLMProvider]:
    if settings.LLM_API_KEY:
        return GeminiLLMProvider(api_key=settings.LLM_API_KEY)
    return None
