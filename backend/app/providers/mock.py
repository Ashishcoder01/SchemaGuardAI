import json
from typing import Any

from app.providers.base import LLMProvider


class MockProvider(LLMProvider):
    name = "mock"

    async def generate(
        self,
        prompt: str,
        json_schema: dict[str, Any],
        previous_errors: list[str] | None = None,
    ) -> str:
        """
        Generate sample data from a JSON Schema.

        This provider does not use an actual AI model.
        """

        value = self._sample(json_schema)

        return json.dumps(value)

    def _sample(self, schema: dict[str, Any]) -> Any:
        schema_type = schema.get("type")

        if "enum" in schema:
            return schema["enum"][0]

        if "const" in schema:
            return schema["const"]

        if schema_type == "object":
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            result = {}

            for name in required:
                if name in properties:
                    result[name] = self._sample(properties[name])

            return result

        if schema_type == "array":
            item_schema = schema.get("items", {})
            minimum = schema.get("minItems", 1)

            count = max(0, min(minimum, 5))

            return [
                self._sample(item_schema)
                for _ in range(count)
            ]

        if schema_type == "string":
            minimum = schema.get("minLength", 0)

            value = "Sample output"

            if len(value) < minimum:
                value = value + ("x" * (minimum - len(value)))

            return value

        if schema_type == "integer":
            minimum = schema.get("minimum", 0)
            maximum = schema.get("maximum", minimum + 100)

            return int(minimum) if minimum <= maximum else 0

        if schema_type == "number":
            minimum = schema.get("minimum", 0)
            maximum = schema.get("maximum", minimum + 100)

            return float(minimum) if minimum <= maximum else 0.0

        if schema_type == "boolean":
            return True

        if schema_type == "null":
            return None

        for option in schema.get("anyOf", schema.get("oneOf", [])):
            try:
                return self._sample(option)
            except Exception:
                continue

        return None