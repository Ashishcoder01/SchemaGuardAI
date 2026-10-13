import json
from typing import Any
from .config import settings

class ProviderError(RuntimeError):
    pass

class MockProvider:
    name = "mock"
    model = "mock-schema-v1"
    def generate(self, prompt: str, schema: dict[str, Any], model: str | None = None, feedback: str = "") -> str:
        # Deterministic schema-aware output for local demos and tests; no network/API key needed.
        def sample(s: dict[str, Any], key: str = "value"):
            typ = s.get("type", "string")
            if "enum" in s: return s["enum"][0]
            if typ == "object":
                props=s.get("properties", {})
                required=s.get("required", list(props.keys()))
                return {k: sample(props[k], k) for k in props if k in required}
            if typ == "array": return [sample(s.get("items", {"type":"string"}), key)] if s.get("minItems", 0)>0 else []
            if typ == "integer": return int(s.get("minimum", 1))
            if typ == "number": return float(s.get("minimum", 1.0))
            if typ == "boolean": return True
            if typ == "null": return None
            defaults={"title":"Example structured result", "summary":"Generated in local mock mode. Configure an LLM provider for prompt-specific content.", "name":"Example", "email":"example@example.com", "description":"Example value", "tags":["example"]}
            return defaults.get(key, f"Example {key}")
        return json.dumps(sample(schema), ensure_ascii=False)

class OpenAICompatibleProvider:
    name = "openai-compatible"
    def __init__(self):
        if not settings.openai_api_key:
            raise ProviderError("Set OPENAI_API_KEY in backend/.env to use the openai-compatible provider")
    def generate(self, prompt: str, schema: dict[str, Any], model: str | None = None, feedback: str = "") -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url, timeout=settings.request_timeout_seconds)
            system = "Return only one JSON value that conforms exactly to the supplied JSON Schema. Do not use markdown fences."
            if feedback:
                system += " Your previous response failed validation. Correct these issues: " + feedback
            response = client.chat.completions.create(
                model=model or settings.openai_model,
                messages=[{"role":"system","content":system},{"role":"user","content":"JSON Schema:\n"+json.dumps(schema, ensure_ascii=False)+"\n\nTask:\n"+prompt}],
                temperature=0.1,
                response_format={"type":"json_object"},
            )
            content=response.choices[0].message.content
            if not content: raise ProviderError("Provider returned an empty response")
            return content
        except ProviderError: raise
        except Exception as exc:
            raise ProviderError(f"LLM provider request failed: {type(exc).__name__}: {str(exc)[:300]}") from exc

def get_provider(name: str):
    if name == "mock": return MockProvider()
    if name == "openai-compatible": return OpenAICompatibleProvider()
    raise ProviderError(f"Unsupported provider: {name}")
