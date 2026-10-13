import time
from collections import Counter
from typing import Annotated
from app.security import require_api_key

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine as db_engine, get_db
from app.engine import engine as guard_engine
from app.models import RunRecord, SchemaRecord
from app.schemas import GenerateRequest, SchemaCreate


Base.metadata.create_all(bind=db_engine)

app = FastAPI(
    title="SchemaGuard AI",
    description=(
        "Structured output validation, automatic recovery, "
        "and LLM reliability monitoring."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)




DbSession = Annotated[Session, Depends(get_db)]


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/api/providers", dependencies=[Depends(require_api_key)])
def list_providers():
    return {
        "providers": [
            {
                "id": "mock",
                "name": "Mock Provider",
                "requires_api_key": False,
            },
            {
                "id": "openai_compatible",
                "name": "OpenAI-compatible API",
                "requires_api_key": True,
            },
        ],
        "default": settings.llm_provider,
    }


@app.post(
    "/api/generate",
    dependencies=[Depends(require_api_key)],
)
async def generate(
    request: GenerateRequest,
    db: DbSession,
):
    start = time.perf_counter()

    try:
        result = await guard_engine.execute(
            prompt=request.prompt,
            json_schema=request.json_schema,
            provider_name=request.provider,
            max_retries=request.max_retries,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    elapsed = round(
        (time.perf_counter() - start) * 1000,
        2,
    )

    record = RunRecord(
    prompt=request.prompt,
    prompt_preview=request.prompt[:500],
    provider=result["provider"],
    model=result.get("model", result["provider"]),
    status="success" if result["success"] else "failed",
    schema_name=request.schema_name,
    success=result["success"],
    attempts=result["attempts"],
    latency_ms=result["latency_ms"],
    output_json=(
        result["output"]
        if isinstance(result["output"], dict)
        else (
            {"_array_result": result["output"]}
            if isinstance(result["output"], list)
            else None
        )
    ),
    errors_json=result["errors"],
)

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        **result,
        "run_id": record.id,
        "request_latency_ms": elapsed,
    }


@app.post(
    "/api/schemas",
    dependencies=[Depends(require_api_key)],
)
def create_schema(
    request: SchemaCreate,
    db: DbSession,
):
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError

    try:
        Draft202012Validator.check_schema(
            request.schema_definition
        )
    except SchemaError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid JSON Schema: {exc.message}",
        ) from exc

    existing = db.scalar(
        select(SchemaRecord)
        .where(SchemaRecord.name == request.name)
        .order_by(SchemaRecord.version.desc())
    )

    version = existing.version + 1 if existing else 1

    record = SchemaRecord(
    name=request.name,
    description="",
    version=version,
    schema_json=request.schema_definition,
    active=True,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "name": record.name,
        "version": record.version,
        "schema_json": record.schema_json,
    }


@app.get(
    "/api/schemas",
    dependencies=[Depends(require_api_key)],
)
def list_schemas(db: DbSession):
    records = db.scalars(
        select(SchemaRecord)
        .where(SchemaRecord.active.is_(True))
        .order_by(
            SchemaRecord.name,
            SchemaRecord.version.desc(),
        )
    ).all()

    return {
        "schemas": [
            {
                "id": item.id,
                "name": item.name,
                "version": item.version,
                "schema_json": item.schema_json,
                "created_at": item.created_at.isoformat(),
            }
            for item in records
        ]
    }


@app.get(
    "/api/runs",
    dependencies=[Depends(require_api_key)],
)
def list_runs(
    db: DbSession,
    limit: int = 20,
):
    if not 1 <= limit <= 100:
        raise HTTPException(
            status_code=422,
            detail="limit must be between 1 and 100.",
        )

    records = db.scalars(
        select(RunRecord)
        .order_by(RunRecord.id.desc())
        .limit(limit)
    ).all()

    return {
        "runs": [
            {
                "id": item.id,
                "provider": item.provider,
                "schema_name": item.schema_name,
                "success": item.success,
                "attempts": item.attempts,
                "latency_ms": item.latency_ms,
                "errors": item.errors_json,
                "created_at": item.created_at.isoformat(),
            }
            for item in records
        ]
    }


@app.get(
    "/api/metrics",
    dependencies=[Depends(require_api_key)],
)
def metrics(db: DbSession):
    total = db.scalar(
        select(func.count()).select_from(RunRecord)
    ) or 0

    successful = db.scalar(
        select(func.count())
        .select_from(RunRecord)
        .where(RunRecord.success.is_(True))
    ) or 0

    failed = total - successful

    average_latency = db.scalar(
        select(func.avg(RunRecord.latency_ms))
    )

    average_attempts = db.scalar(
        select(func.avg(RunRecord.attempts))
    )

    provider_rows = db.execute(
        select(
            RunRecord.provider,
            func.count(),
        ).group_by(RunRecord.provider)
    ).all()

    return {
        "total_runs": total,
        "successful_runs": successful,
        "failed_runs": failed,
        "success_rate": round(
            successful / total * 100, 2
        ) if total else 0,
        "average_latency_ms": round(
            average_latency, 2
        ) if average_latency is not None else 0,
        "average_attempts": round(
            average_attempts, 2
        ) if average_attempts is not None else 0,
        "runs_by_provider": {
            name: count for name, count in provider_rows
        },
    }