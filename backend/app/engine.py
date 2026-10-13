import json
import time
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from app.config import settings
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider
from app.providers.openai_compatible import OpenAICompatibleProvider


class SchemaGuardEngine:
    def __init__(self):
        self.providers: dict[str, LLMProvider] = {
            "mock": MockProvider(),
            "openai_compatible": OpenAICompatibleProvider(),
        }

    async def execute(
        self,
        prompt: str,
        json_schema: dict[str, Any],
        provider_name: str | None = None,
        max_retries: int | None = None,
    ) -> dict[str, Any]:

        provider_name = provider_name or settings.llm_provider
        provider = self.providers.get(provider_name)

        if provider is None:
            raise ValueError(
                f"Unsupported provider: {provider_name}"
            )

        retries = (
            settings.max_retries
            if max_retries is None
            else max_retries
        )

        if not 0 <= retries <= 5:
            raise ValueError(
                "max_retries must be between 0 and 5."
            )

        try:
            Draft202012Validator.check_schema(json_schema)
        except SchemaError as exc:
            raise ValueError(
                f"Invalid JSON Schema: {exc.message}"
            ) from exc

        validator = Draft202012Validator(json_schema)
        errors: list[str] = []
        start = time.perf_counter()

        for attempt in range(1, retries + 2):
            try:
                raw_output = await provider.generate(
                    prompt=prompt,
                    json_schema=json_schema,
                    previous_errors=errors or None,
                )

                output = json.loads(raw_output)

                validation_errors = sorted(
                    validator.iter_errors(output),
                    key=lambda error: list(
                        map(str, error.absolute_path)
                    ),
                )

                if validation_errors:
                    errors = [
                        (
                            f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: "
                            f"{error.message}"
                        )
                        for error in validation_errors
                    ]
                    continue

                return {
                    "success": True,
                    "output": output,
                    "provider": provider_name,
                    "attempts": attempt,
                    "latency_ms": round(
                        (time.perf_counter() - start) * 1000,
                        2,
                    ),
                    "errors": errors,
                }

            except json.JSONDecodeError as exc:
                errors = [
                    f"Invalid JSON at character {exc.pos}."
                ]

            except Exception as exc:
                errors = [
                    f"Provider or execution error: {type(exc).__name__}"
                ]

        return {
            "success": False,
            "output": None,
            "provider": provider_name,
            "attempts": retries + 1,
            "latency_ms": round(
                (time.perf_counter() - start) * 1000,
                2,
            ),
            "errors": errors,
        }


engine = SchemaGuardEngine()