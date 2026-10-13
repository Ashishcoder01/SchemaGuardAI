
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import ValidationError
from app.config import Settings

from app.database import Base, get_db
from app.main import app
from app.models import RunRecord, SchemaRecord


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_health_endpoint(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_providers(client):
    response = client.get("/api/providers")

    assert response.status_code == 200
    provider_ids = {
        provider["id"]
        for provider in response.json()["providers"]
    }
    assert "mock" in provider_ids
    assert "openai_compatible" in provider_ids


def test_create_and_list_schema(client):
    payload = {
        "name": "API Test Person",
        "schema_json": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name", "age"],
            "additionalProperties": False,
        },
    }

    create_response = client.post(
        "/api/schemas",
        json=payload,
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == payload["name"]
    assert created["version"] == 1
    assert created["schema_json"] == payload["schema_json"]

    list_response = client.get("/api/schemas")

    assert list_response.status_code == 200
    schemas = list_response.json()["schemas"]
    assert any(item["id"] == created["id"] for item in schemas)


def test_invalid_json_schema_is_rejected(client):
    response = client.post(
        "/api/schemas",
        json={
            "name": "Invalid Schema",
            "schema_json": {"type": "not-a-valid-type"},
        },
    )

    assert response.status_code == 422


def test_generate_records_run(client):
    response = client.post(
        "/api/generate",
        json={
            "prompt": "Generate a person",
            "schema_name": "API Test Person",
            "provider": "mock",
            "max_retries": 0,
            "json_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                },
                "required": ["name", "age"],
                "additionalProperties": False,
            },
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True
    assert result["output"]["name"]
    assert isinstance(result["output"]["age"], int)
    assert result["run_id"]

    runs_response = client.get("/api/runs")
    assert runs_response.status_code == 200

    runs = runs_response.json()["runs"]
    assert any(run["id"] == result["run_id"] for run in runs)


def test_metrics_reflect_test_database(client):
    generate_response = client.post(
        "/api/generate",
        json={
            "prompt": "Generate a short answer",
            "provider": "mock",
            "max_retries": 0,
            "json_schema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                },
                "required": ["answer"],
                "additionalProperties": False,
            },
        },
    )

    assert generate_response.status_code == 200

    response = client.get("/api/metrics")

    assert response.status_code == 200
    metrics = response.json()
    assert metrics["total_runs"] == 1
    assert metrics["successful_runs"] == 1
    assert metrics["failed_runs"] == 0
    assert metrics["success_rate"] == 100.0



from app.config import settings


def test_protected_endpoint_allows_local_development_without_key(
    client, monkeypatch
):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "api_key", "")

    response = client.get("/api/providers")

    assert response.status_code == 200


def test_protected_endpoint_rejects_missing_key(
    client, monkeypatch
):
    monkeypatch.setattr(settings, "api_key", "test-secret-key")

    response = client.get("/api/providers")

    assert response.status_code == 401


def test_protected_endpoint_rejects_invalid_key(
    client, monkeypatch
):
    monkeypatch.setattr(settings, "api_key", "test-secret-key")

    response = client.get(
        "/api/providers",
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401


def test_protected_endpoint_accepts_valid_key(
    client, monkeypatch
):
    monkeypatch.setattr(settings, "api_key", "test-secret-key")

    response = client.get(
        "/api/providers",
        headers={"X-API-Key": "test-secret-key"},
    )

    assert response.status_code == 200



def test_production_without_api_key_returns_503(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "api_key", "")

    response = client.get("/api/providers")

    assert response.status_code == 503
    assert response.json()["detail"] == "API authentication is not configured."



def test_cors_allows_configured_development_origin(client):
    response = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:5173"
    )


def test_cors_does_not_allow_unconfigured_origin(client):
    response = client.get(
        "/api/health",
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_production_rejects_wildcard_cors_origin():
    try:
        Settings(
            environment="production",
            cors_origins="*",
        )
    except ValidationError:
        pass
    else:
        raise AssertionError(
            "Production must reject wildcard CORS origins."
        )


def test_production_rejects_localhost_cors_origin():
    try:
        Settings(
            environment="production",
            cors_origins="http://localhost:5173",
        )
    except ValidationError:
        pass
    else:
        raise AssertionError(
            "Production must reject localhost CORS origins."
        )


def test_production_accepts_explicit_https_origin():
    config = Settings(
        environment="production",
        cors_origins="https://app.example.com",
        api_key="test-production-key",
    )

    assert config.allowed_origins == ["https://app.example.com"]
