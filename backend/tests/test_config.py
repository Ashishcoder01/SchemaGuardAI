
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices


class SettingsForTest(BaseSettings):
    api_key: str = Field(
        default="",
        validation_alias=AliasChoices("SCHEMAGUARD_API_KEY", "API_KEY"),
    )

    model_config = SettingsConfigDict(extra="ignore")


def test_schemagaurd_api_key_is_supported(monkeypatch):
    monkeypatch.setenv("SCHEMAGUARD_API_KEY", "primary-test-key")
    monkeypatch.delenv("API_KEY", raising=False)

    settings = SettingsForTest()

    assert settings.api_key == "primary-test-key"


def test_legacy_api_key_is_supported(monkeypatch):
    monkeypatch.delenv("SCHEMAGUARD_API_KEY", raising=False)
    monkeypatch.setenv("API_KEY", "legacy-test-key")

    settings = SettingsForTest()

    assert settings.api_key == "legacy-test-key"


def test_api_key_defaults_to_empty(monkeypatch):
    monkeypatch.delenv("SCHEMAGUARD_API_KEY", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)

    settings = SettingsForTest()

    assert settings.api_key == ""

def test_schemagaurd_api_key_takes_precedence(monkeypatch):
    monkeypatch.setenv("SCHEMAGUARD_API_KEY", "primary-test-key")
    monkeypatch.setenv("API_KEY", "legacy-test-key")

    settings = SettingsForTest()

    assert settings.api_key == "primary-test-key"