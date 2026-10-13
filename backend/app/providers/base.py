from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        json_schema: dict[str, Any],
        previous_errors: list[str] | None = None,
    ) -> str:
        """Return the model's raw text response."""
        raise NotImplementedError