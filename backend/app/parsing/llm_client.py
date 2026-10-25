"""Ollama LLM client for intent extraction and grounded explanations.

Includes strict input sanitization, retry with backoff, configurable timeout,
and graceful fallback when the Ollama service is unavailable.
"""

import asyncio
import re
import time
from typing import Any

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger("zero-friction-transit")


def sanitize_untrusted_input(text: str, max_chars: int = 300) -> str:
    """
    Sanitize untrusted user query before passing to LLM.
    Strips non-printable control characters, collapses whitespace, and limits length.
    """
    if not text:
        return ""
    # Strip non-printable ASCII control characters
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Collapse multiple whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_chars]


class OllamaClient:
    """Client for local Ollama instance with timeout and retry."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL
        self.timeout = float(timeout_seconds or settings.LLM_TIMEOUT_SECONDS)

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        response_format: str = "json",
    ) -> str | None:
        """
        Synchronous call to Ollama generate endpoint with 1 retry.
        Returns the raw model text response, or None if unavailable.
        """
        if not settings.LLM_ENABLED:
            logger.debug("LLM disabled in application settings. Skipping Ollama call.")
            return None

        url = f"{self.base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "system": system_instruction,
            "stream": False,
            "format": response_format,
            "options": {
                "temperature": 0.0,
                "top_p": 0.9,
            },
        }

        # Attempt call with 1 retry
        for attempt in range(2):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    response_text = data.get("response", "")
                    return str(response_text)
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                logger.warning(
                    "Ollama request failed",
                    attempt=attempt + 1,
                    model=self.model,
                    error=str(exc),
                )
                if attempt == 0:
                    time.sleep(0.5)

        logger.info("Ollama unavailable or timed out; falling back gracefully.")
        return None

    async def generate_async(
        self,
        prompt: str,
        system_instruction: str,
        response_format: str = "json",
    ) -> str | None:
        """Asynchronous call to Ollama generate endpoint."""
        if not settings.LLM_ENABLED:
            return None

        url = f"{self.base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "system": system_instruction,
            "stream": False,
            "format": response_format,
            "options": {
                "temperature": 0.0,
            },
        }

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    return str(data.get("response", ""))
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                logger.warning(
                    "Ollama async request failed",
                    attempt=attempt + 1,
                    error=str(exc),
                )
                if attempt == 0:
                    await asyncio.sleep(0.5)

        return None


default_ollama_client = OllamaClient()
