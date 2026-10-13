# SchemaGuard AI

**Reliable structured outputs for LLM applications.**

SchemaGuard AI is a full-stack application that runs an LLM provider, parses its response as JSON, validates the result against a JSON Schema, retries when necessary, and records run history and reliability metrics. A React dashboard provides a playground for testing prompts and inspecting results.

<p align="center">
  <a href="https://schemaguard-ai-demo.onrender.com/"><strong>Live Demo</strong></a>
  &nbsp;·&nbsp;
  <a href="https://schemaguard-ai-api.onrender.com/api/health">API Health</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/Ashishcoder01/SchemaGuardAI">Source Code</a>
</p>

> **Demo note:** The frontend connects to a deployed API. Availability depends on the hosting service and its current configuration. The API may require an API key; enter it in the dashboard settings if your deployment is configured to require one. Never share a production key publicly.

## What it does

- **Schema validation:** checks generated JSON against JSON Schema Draft 2020-12.
- **Bounded retries:** gives the provider validation feedback and retries invalid output up to the configured limit.
- **Provider adapters:** supports a deterministic mock provider for local development and an OpenAI-compatible chat-completions provider.
- **Execution history:** persists run metadata and lets the dashboard inspect recent executions.
- **Reliability metrics:** summarizes successful and failed runs, success rate, latency, attempts, and provider usage.
- **API-key protection:** protected API routes can require an `X-API-Key` header.
- **Configurable storage:** SQLite is the default for local development; the Docker Compose setup uses PostgreSQL.
- **Automated tests:** backend tests cover API, configuration, database, and engine behavior.

## Live links

| Resource | Link |
| --- | --- |
| Web dashboard | [schemaguard-ai-demo.onrender.com](https://schemaguard-ai-demo.onrender.com/) |
| Backend health | [API health endpoint](https://schemaguard-ai-api.onrender.com/api/health) |
| API documentation (if enabled by deployment) | [FastAPI docs](https://schemaguard-ai-api.onrender.com/docs) |
| GitHub repository | [Ashishcoder01/SchemaGuardAI](https://github.com/Ashishcoder01/SchemaGuardAI) |

The health endpoint is public in the current backend. Other endpoints may require an API key.

## Architecture

```text
React + TypeScript dashboard
          |
          | HTTP / JSON (X-API-Key when configured)
          v
       FastAPI API
          |
          v
   SchemaGuardEngine
     |           |
     |           +--> JSON parsing and JSON Schema validation
     v
 Provider adapter
   |         |
 Mock     OpenAI-compatible API
          |
          v
 SQLAlchemy persistence --> SQLite (local) / PostgreSQL (Docker setup)
          |
          +--> Run history and reliability metrics
```

The mock provider creates deterministic, schema-shaped example data. It is useful for testing the interface and validation workflow, but it does **not** generate prompt-grounded AI responses. Configure a real provider for actual inference.

## Technology stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Three.js, Lucide |
| Backend | Python, FastAPI, Pydantic |
| Validation | JSON Schema Draft 2020-12, `jsonschema` |
| Persistence | SQLAlchemy, SQLite, PostgreSQL |
| Provider integration | Mock provider, OpenAI-compatible chat completions |
| Testing | pytest |
| Deployment | Render links for the hosted demo; Docker Compose for local container deployment |

## Screens and workflow

1. Open the playground and enter a prompt.
2. Choose a provider and provide a JSON Schema.
3. Run generation and inspect the result, validation status, attempts, and errors.
4. Review execution history and reliability metrics.
5. Configure the API URL and API key in dashboard settings when required by the deployment.

## Run locally (Windows PowerShell)

### Prerequisites

- Python 3.12 recommended
- Node.js and npm
- Git

### 1. Start the backend

Open PowerShell in the repository root:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks virtual-environment activation, run the environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

The local API is available at [http://127.0.0.1:8000](http://127.0.0.1:8000). FastAPI's interactive docs are at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 2. Start the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). By default, the frontend calls `http://127.0.0.1:8000`. To use a different API, create `frontend/.env.local` with:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Restart the Vite server after changing environment variables.

### 3. Configure an LLM provider

The mock provider works without a third-party API key. For real inference, configure the backend environment:

```env
LLM_PROVIDER=openai_compatible
OPENAI_API_KEY=your-provider-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

Use the base URL, model name, and structured-output features supported by your selected OpenAI-compatible provider. Keep provider credentials on the backend only—never place them in frontend environment variables or commit them to Git.

### Environment settings

The backend reads `.env` from its working directory. Common settings include:

| Variable | Purpose |
| --- | --- |
| `ENVIRONMENT` | Runtime mode; use `production` for production deployments |
| `DATABASE_URL` | SQLAlchemy database connection URL |
| `SCHEMAGUARD_API_KEY` or `API_KEY` | API key for protected routes |
| `LLM_PROVIDER` | Default provider, e.g. `mock` or `openai_compatible` |
| `OPENAI_API_KEY` | Provider credential (backend only) |
| `OPENAI_BASE_URL` | Provider API base URL |
| `OPENAI_MODEL` | Model identifier |
| `MAX_RETRIES` | Maximum retry count used by the engine configuration |
| `CORS_ORIGINS` | Comma-separated allowed browser origins |
| `REQUEST_TIMEOUT` | Provider request timeout in seconds |

Use a long, unique secret for API authentication in production. Production CORS configuration must contain explicit trusted origins; wildcard origins and local HTTP origins are rejected by the current settings validator.

## API overview

The current backend exposes these primary endpoints:

| Method | Endpoint | Purpose | Authentication |
| --- | --- | --- | --- |
| `GET` | `/api/health` | Health status | Public |
| `GET` | `/api/providers` | Available provider metadata | API key |
| `POST` | `/api/generate` | Generate, parse, validate, and record an output | API key |
| `POST` | `/api/schemas` | Save a schema version | API key |
| `GET` | `/api/schemas` | List saved schemas | API key |
| `GET` | `/api/runs?limit=20` | Read recent run history (limit 1–100) | API key |
| `GET` | `/api/metrics` | Read aggregate reliability metrics | API key |

Protected endpoints expect the `X-API-Key` request header when API-key authentication is configured. Check the live API's `/docs` page for the exact request and response schemas supported by the deployed version.

## Tests and production build

Backend tests:

```powershell
cd backend
python -m pytest -q
```

Frontend TypeScript check and production build:

```powershell
cd frontend
npm install
npm run build
```

The frontend build currently succeeds. Vite may report a large JavaScript chunk because the animated background uses Three.js; code-splitting is a potential future optimization.

## Docker Compose

The repository includes a Docker Compose setup with PostgreSQL, backend, and frontend services. From the repository root:

1. Create a root `.env` file containing strong, unique values for `POSTGRES_PASSWORD` and `API_KEY`.
2. Set `CORS_ORIGINS` to the exact trusted frontend origin for your environment.
3. Add provider credentials only if using a real LLM provider.
4. Start the services:

```powershell
docker compose up --build -d
docker compose logs -f backend
```

The Compose file binds the backend port to localhost and serves the frontend on port 8080 by default. Review the Compose configuration and environment values before exposing any service publicly. Never use sample or weak secrets for a public deployment.

## Security and data considerations

- Never commit `.env` files, API keys, database credentials, or private user data.
- Keep provider API keys on the backend.
- Use HTTPS and a strong API key in production.
- Configure CORS for known frontend origins; CORS is not a replacement for authentication.
- Run history can include user prompts and output/error metadata. Avoid sending sensitive data and establish retention controls before production use.
- Before changing database models, use a migration strategy and back up the database. Do not delete or recreate a production database to apply schema changes.
- Multi-user access requires additional identity, authorization, and tenant-isolation controls.

## Roadmap

- Improve frontend bundle splitting and loading performance.
- Add schema registry management workflows to the dashboard.
- Add database migrations and documented backup/restore procedures.
- Improve provider-specific structured-output compatibility and observability.
- Add rate limiting, quotas, and stronger multi-user authorization for production use.

## Contributing

Issues and pull requests are welcome. Please run backend tests and the frontend production build before submitting changes, and do not include secrets in commits.

## License

No license file is currently documented in this repository. Add a license before granting others explicit permission to reuse, modify, or redistribute the project.
