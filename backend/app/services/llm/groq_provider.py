"""
Groq implementation of LLMProvider.

Reads GROQ_API_KEY and GROQ_MODEL from environment variables via
app.core.config. Never exposes the API key to callers or the frontend.
"""
import json
import logging
from typing import Any

from groq import Groq

from app.core.config import get_settings
from app.services.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.GROQ_API_KEY:
            logger.warning(
                "GROQ_API_KEY is not set. GroqProvider calls will fail until it is configured in .env"
            )
        self._client = Groq(api_key=settings.GROQ_API_KEY or "missing-key")
        self._model = settings.GROQ_MODEL

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )
        return completion.choices[0].message.content or ""


    def generate_structured(
        self,
        prompt: str,
        schema_hint: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        structured_system = (
            (system_prompt or "")
            + "\n\nReturn ONLY a valid JSON object matching this shape. "
            + "Do not include markdown, explanations, or code fences.\n"
            + schema_hint
        )

        messages = [
            {"role": "system", "content": structured_system},
            {"role": "user", "content": prompt},
        ]

        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.1,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            raw = completion.choices[0].message.content or ""
            result = json.loads(raw)

            if not isinstance(result, dict):
                logger.warning("Groq returned JSON that was not an object")
                return {"error": "invalid_json"}

            return result

        except json.JSONDecodeError:
            logger.warning("Groq returned invalid JSON")
            return {"error": "invalid_json"}

        except Exception as exc:
            logger.warning(
                "Groq structured generation failed (%s)",
                type(exc).__name__,
            )
            return {"error": "provider_error"}
