
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=12000)
    schema_name: str = Field(
        default="default",
        min_length=1,
        max_length=150,
    )
    json_schema: dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
            },
            "required": ["answer"],
            "additionalProperties": False,
        }
    )
    provider: Literal[
        "mock",
        "openai_compatible",
    ] | None = None

    max_retries: int = Field(default=2, ge=0, le=5)


class GenerateResponse(BaseModel):
    success: bool
    output: dict[str, Any] | list[Any] | None = None
    provider: str
    attempts: int
    latency_ms: float
    errors: list[str] = Field(default_factory=list)


class SchemaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    schema_definition: dict[str, Any] = Field(
        validation_alias="schema_json",
        serialization_alias="schema_json",
    )
