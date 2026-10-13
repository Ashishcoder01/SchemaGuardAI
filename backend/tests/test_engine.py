import json

import pytest

from app.engine import SchemaGuardEngine
from app.providers.base import LLMProvider


class SequenceProvider(LLMProvider):
    name = "test"

    def __init__(self, responses):
        self.responses = iter(responses)

    async def generate(
        self,
        prompt,
        json_schema,
        previous_errors=None,
    ):
        return next(self.responses)


@pytest.mark.asyncio
async def test_valid_output():
    engine = SchemaGuardEngine()

    result = await engine.execute(
        prompt="Generate an answer",
        json_schema={
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"],
            "additionalProperties": False,
        },
        provider_name="mock",
        max_retries=0,
    )

    assert result["success"] is True
    assert isinstance(result["output"]["answer"], str)


@pytest.mark.asyncio
async def test_invalid_output_is_retried():
    engine = SchemaGuardEngine()
    provider = SequenceProvider([
        '{"answer": 123}',
        '{"answer": "Corrected"}',
    ])

    engine.providers["test"] = provider

    result = await engine.execute(
        prompt="Generate an answer",
        json_schema={
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"],
            "additionalProperties": False,
        },
        provider_name="test",
        max_retries=1,
    )

    assert result["success"] is True
    assert result["attempts"] == 2
    assert result["output"]["answer"] == "Corrected"


@pytest.mark.asyncio
async def test_malformed_json_is_retried():
    engine = SchemaGuardEngine()
    engine.providers["test"] = SequenceProvider([
        "{invalid json",
        '{"answer": "Recovered"}',
    ])

    result = await engine.execute(
        prompt="Generate an answer",
        json_schema={
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"],
        },
        provider_name="test",
        max_retries=1,
    )

    assert result["success"] is True
    assert result["attempts"] == 2


@pytest.mark.asyncio
async def test_exhausted_retries_return_failure():
    engine = SchemaGuardEngine()
    engine.providers["test"] = SequenceProvider([
        '{"answer": 123}',
        '{"answer": 456}',
    ])

    result = await engine.execute(
        prompt="Generate an answer",
        json_schema={
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"],
        },
        provider_name="test",
        max_retries=1,
    )

    assert result["success"] is False
    assert result["attempts"] == 2
    assert result["output"] is None
    assert result["errors"]


def test_invalid_schema_is_rejected():
    import asyncio

    engine = SchemaGuardEngine()

    with pytest.raises(ValueError):
        asyncio.run(
            engine.execute(
                prompt="Test",
                json_schema={"type": "invalid-type"},
                provider_name="mock",
                max_retries=0,
            )
        )


@pytest.mark.asyncio
async def test_zero_retries_makes_only_one_attempt():
    engine = SchemaGuardEngine()
    provider = SequenceProvider([
        '{"answer": 123}',
        '{"answer": "Should not be reached"}',
    ])
    engine.providers["test"] = provider

    result = await engine.execute(
        prompt="Generate an answer",
        json_schema={
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"],
        },
        provider_name="test",
        max_retries=0,
    )

    assert result["success"] is False
    assert result["attempts"] == 1
    assert result["errors"]


@pytest.mark.asyncio
async def test_retry_passes_previous_validation_errors():
    class InspectingProvider(LLMProvider):
        name = "test"

        def __init__(self):
            self.calls = []

        async def generate(
            self,
            prompt,
            json_schema,
            previous_errors=None,
        ):
            self.calls.append(previous_errors)

            if len(self.calls) == 1:
                return '{"answer": 123}'

            return '{"answer": "Recovered"}'

    engine = SchemaGuardEngine()
    provider = InspectingProvider()
    engine.providers["test"] = provider

    result = await engine.execute(
        prompt="Generate an answer",
        json_schema={
            "type": "object",
            "properties": {
                "answer": {"type": "string"}
            },
            "required": ["answer"],
        },
        provider_name="test",
        max_retries=1,
    )

    assert result["success"] is True
    assert result["attempts"] == 2
    assert provider.calls[0] is None
    assert provider.calls[1]
    assert "string" in provider.calls[1][0].lower()



@pytest.mark.asyncio
async def test_nested_object_and_array_schema():
    engine = SchemaGuardEngine()

    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                },
                "required": ["name", "age"],
                "additionalProperties": False,
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["user", "tags"],
        "additionalProperties": False,
    }

    result = await engine.execute(
        prompt="Generate a user profile",
        json_schema=schema,
        provider_name="mock",
        max_retries=0,
    )

    assert result["success"] is True
    assert isinstance(result["output"]["user"], dict)
    assert isinstance(result["output"]["user"]["name"], str)
    assert isinstance(result["output"]["user"]["age"], int)
    assert isinstance(result["output"]["tags"], list)


@pytest.mark.asyncio
async def test_missing_required_field_is_retried():
    engine = SchemaGuardEngine()
    engine.providers["test"] = SequenceProvider([
        '{"name": "Alex"}',
        '{"name": "Alex", "age": 21}',
    ])

    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name", "age"],
        "additionalProperties": False,
    }

    result = await engine.execute(
        prompt="Generate a person",
        json_schema=schema,
        provider_name="test",
        max_retries=1,
    )

    assert result["success"] is True
    assert result["attempts"] == 2
    assert result["output"]["age"] == 21


@pytest.mark.asyncio
async def test_additional_property_is_rejected():
    engine = SchemaGuardEngine()
    engine.providers["test"] = SequenceProvider([
        '{"answer": "Hello", "extra": true}',
        '{"answer": "Hello"}',
    ])

    schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
        },
        "required": ["answer"],
        "additionalProperties": False,
    }

    result = await engine.execute(
        prompt="Generate an answer",
        json_schema=schema,
        provider_name="test",
        max_retries=1,
    )

    assert result["success"] is True
    assert result["attempts"] == 2
    assert "extra" not in result["output"]


@pytest.mark.asyncio
async def test_retry_limit_above_five_is_rejected():
    engine = SchemaGuardEngine()

    with pytest.raises(ValueError, match="max_retries"):
        await engine.execute(
            prompt="Test",
            json_schema={"type": "object"},
            provider_name="mock",
            max_retries=6,
        )
