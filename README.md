# SchemaGuard AI

SchemaGuard AI is a full-stack structured-output reliability platform for LLM applications. It validates model responses against JSON Schema, retries invalid output with validation feedback, records execution history, and provides a React dashboard for inspection.

## Features

- React + TypeScript dashboard with playground, schema registry, execution history, metrics, and settings.
- FastAPI backend with OpenAPI documentation.
- JSON Schema Draft 2020-12 validation plus Pydantic-based input/data validation.
- Bounded retries and validation feedback; invalid output is never reported as successful.
- Provider adapters: deterministic mock provider and OpenAI-compatible chat-completions APIs.
- SQLite by default for local development; PostgreSQL through Docker Compose.
- Configurable API-key authentication, request-size limits, structured server logs, tests, and container build.

## Architecture

`React UI -> FastAPI -> StructuredOutputEngine -> Provider adapter -> independent JSON Schema validator -> SQLAlchemy run history`

The mock provider is intended for UI development and deterministic tests. It generates schema-shaped examples, not prompt-grounded AI content. Use a configured LLM provider for real inference.

## Local development (Windows PowerShell)

### 1. Backend

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks activation, use `\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000` instead.

API docs: http://127.0.0.1:8000/docs
Health: http://127.0.0.1:8000/api/health

### 2. Frontend (second terminal)

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The app uses `http://localhost:8000` by default. To change it, create `frontend/.env.local` with `VITE_API_URL=http://localhost:8000` and restart Vite.

### 3. Use a real provider

Edit `backend/.env`:

```env
OPENAI_API_KEY=your-provider-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

For another OpenAI-compatible service, set its documented API base URL and model. Select **OpenAI-compatible API** in the playground. The exact model and structured-output capabilities depend on the provider. Keep API keys only in the backend environment, never in `frontend/.env`.

## Docker deployment

1. Copy root `.env.example` to `.env`.
2. Replace the sample database and API key values with long, unique secrets.
3. Set `CORS_ORIGINS` to the trusted frontend origin. The frontend is served by Nginx at `http://localhost:8080`; the API is available at `http://localhost:8000`. For split deployments, set `VITE_API_URL` to the public API URL and rebuild the frontend.
4. Run:

```powershell
docker compose up --build -d
docker compose logs -f api
```

Open the dashboard at `http://localhost:8080`. Since Compose enables API-key authentication, open Settings in the dashboard and enter the value of `SCHEMAGUARD_API_KEY` from the root `.env` file (the unsafe sample default is `change-this-api-key`; replace it before use). API docs are available at `http://localhost:8000/docs`. Do not expose API docs publicly without considering your deployment policy.

## Tests

```powershell
cd backend
python -m pytest -q
```

## API overview

- `GET /api/health` — health status (public)
- `GET /api/config` — supported providers and default schema
- `POST /api/run` — run generation, parsing, validation, and bounded recovery
- `GET /api/runs?limit=25` — recent executions
- `GET /api/metrics` — aggregate success and latency metrics
- `GET /api/schemas` — list saved schemas
- `POST /api/schemas` — create a schema
- `PUT /api/schemas/{id}` — update and version a schema
- `DELETE /api/schemas/{id}` — delete a schema

If `SCHEMAGUARD_API_KEY` is set, protected routes require the `X-API-Key` header. Configure `ENVIRONMENT=production` and a strong API key in production. The demo defaults are not a substitute for production secrets management, TLS termination, rate limiting, and access-control review.

## Production hardening checklist

- [ ] Set unique secrets and a managed PostgreSQL database.
- [ ] Terminate TLS at a trusted reverse proxy or hosting platform.
- [ ] Add per-user identities, roles, and tenant isolation before multi-user exposure.
- [ ] Add request rate limits and quotas at the gateway.
- [ ] Set retention policies and avoid storing sensitive prompt content.
- [ ] Add migrations (Alembic) before changing database models.
- [ ] Add provider-specific structured-output support and usage/cost telemetry where available.
- [ ] Add monitoring, alerting, backups, and deployment health checks.

## License

Choose a license before public distribution.
