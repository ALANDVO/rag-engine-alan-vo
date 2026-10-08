import json
import re
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings


def redact_sensitive(text: str) -> str:
    if not text:
        return ""
    # Redact any bearer tokens, api keys, or sensitive patterns
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9\-_\.]+", r"\1[REDACTED]", text, flags=re.IGNORECASE)
    text = re.sub(r"(key=)[A-Za-z0-9\-_\.]+", r"\1[REDACTED]", text, flags=re.IGNORECASE)
    text = re.sub(r"(x-api-key['\":\s]+)[A-Za-z0-9\-_\.]+", r"\1[REDACTED]", text, flags=re.IGNORECASE)
    if settings.llm_api_key:
        text = text.replace(settings.llm_api_key, "[REDACTED_API_KEY]")
    return text


class LLMService:
    def __init__(self):
        self.api_key = settings.llm_api_key
        self.provider = settings.llm_provider.lower()
        self.model = settings.llm_model
        self.base_url = settings.llm_base_url.rstrip("/")
        self.timeout = settings.llm_timeout

    def is_configured(self) -> bool:
        return bool(self.api_key or self.provider == "ollama")

    async def generate_response(
        self,
        prompt: str,
        system_instruction: str = "You are a grounded RAG assistant. Every answer must cite context chunks inline as [1], [2].",
        context_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        # If no API key is configured or offline mode, run deterministic synthesizer
        if not self.is_configured():
            return self._synthesize_offline(prompt, context_chunks or [])

        try:
            if self.provider == "openai-compatible":
                answer = await self._call_openai(prompt, system_instruction)
            elif self.provider == "anthropic":
                answer = await self._call_anthropic(prompt, system_instruction)
            elif self.provider == "gemini":
                answer = await self._call_gemini(prompt, system_instruction)
            elif self.provider == "ollama":
                answer = await self._call_ollama(prompt, system_instruction)
            else:
                answer = await self._call_openai(prompt, system_instruction)

            return {
                "answer": answer,
                "provider": self.provider,
                "model": self.model,
                "advisory": True,
            }
        except httpx.HTTPError as e:
            redacted_err = redact_sensitive(str(e))
            raise RuntimeError(f"LLM provider '{self.provider}' request failed: {redacted_err}") from None

    async def _call_openai(self, prompt: str, system: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_anthropic(self, prompt: str, system: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": self.model,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    async def _call_gemini(self, prompt: str, system: str) -> str:
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_ollama(self, prompt: str, system: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]

    def _synthesize_offline(self, prompt: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deterministic offline grounded synthesis when no API key is provided."""
        if not context_chunks:
            return {
                "answer": "No relevant context found in the indexed documents to answer this question.",
                "provider": "deterministic-offline",
                "model": "offline-rule-engine",
                "advisory": True,
            }

        sentences = []
        for i, chunk in enumerate(context_chunks[:4], 1):
            text = chunk.get("text", "").strip()
            # Extract first substantive sentence
            first_sent = text.split(". ")[0].strip()
            if first_sent and len(first_sent) > 20:
                sentences.append(f"{first_sent} [{i}].")

        if sentences:
            synthesized = "Based on retrieved records:\n" + " ".join(sentences)
        else:
            synthesized = f"Retrieved context records match the query [{1}]."

        return {
            "answer": synthesized,
            "provider": "deterministic-offline",
            "model": "offline-rule-engine",
            "advisory": True,
        }


llm_service = LLMService()
