import json
from typing import Any

import httpx

from app.config import settings
from app.providers.base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    async def generate(
        self,
        prompt: str,
        json_schema: dict[str, Any],
        previous_errors: list[str] | None = None,
    ) -> str:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured."
            )

        correction = ""

        if previous_errors:
            correction = (
                "\nYour previous response failed validation. "
                "Correct these issues:\n"
                + "\n".join(previous_errors)
            )

        system_prompt = (
            "Return only a JSON value that conforms to the "
            "provided JSON Schema. Do not include markdown "
            "or explanatory text.\n"
            "JSON Schema:\n"
            + json.dumps(json_schema)
            + correction
        )

        url = (
            settings.openai_base_url.rstrip("/")
            + "/chat/completions"
        )

        payload = {
            "model": settings.openai_model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": (
                f"Bearer {settings.openai_api_key}"
            ),
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=settings.request_timeout
        ) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )

            response.raise_for_status()
            data = response.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "Provider returned an unexpected response."
            ) from exc
        