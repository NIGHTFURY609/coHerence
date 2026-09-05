"""Groq chat completions. Tests use MockTextClient. No key in this file."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol

from oxygen.constants import GROQ_BASE_URL, TEXT_MODEL


class TextClient(Protocol):
    def complete(self, system: str, user: str) -> str:
        """Raw model text. Dev 2 owns the prompt."""


class MockTextClient:
    def __init__(self, text: str = "ok") -> None:
        self.text = text
        self.last_system = ""
        self.last_user = ""

    def complete(self, system: str, user: str) -> str:
        self.last_system = system
        self.last_user = user
        return self.text


class GpuTextClient:
    """Qwen3.5-9B on the shared B300. Same lock as Helium/Nitrogen."""

    def complete(self, system: str, user: str) -> str:
        from helium.runtime import invoke_gpu

        return invoke_gpu("oxygen_complete", system, user)


class GroqTextClient:
    """openai/gpt-oss-20b on Groq. Reads GROQ_API_KEY from the environment."""

    def complete(self, system: str, user: str) -> str:
        key = os.environ.get("GROQ_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set")
        body = json.dumps(
            {
                "model": TEXT_MODEL,
                "temperature": 0.0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{GROQ_BASE_URL}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "oxygen-coherence/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Groq HTTP {exc.code}: {detail}") from exc
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("Groq returned no choices")
        message = choices[0].get("message") or {}
        text = (message.get("content") or "").strip()
        if not text:
            raise RuntimeError("Groq returned empty content")
        return text
