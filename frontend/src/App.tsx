import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  Clock3,
  Code2,
  Copy,
  Database,
  FileJson,
  FlaskConical,
  Gauge,
  KeyRound,
  LayoutDashboard,
  LoaderCircle,
  Play,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Terminal,
  XCircle,
} from "lucide-react";

type Provider = "mock" | "openai_compatible";

type Run = {
  id: number;
  provider: string;
  schema_name: string;
  success: boolean;
  attempts: number;
  latency_ms: number;
  errors: string[];
  created_at: string;
};

type Metrics = {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  success_rate: number;
  average_latency_ms: number;
  average_attempts: number;
};

type Result = {
  success: boolean;
  output: unknown;
  provider: string;
  attempts: number;
  latency_ms: number;
  errors: string[];
  run_id?: number;
};

const DEFAULT_SCHEMA = {
  type: "object",
  properties: {
    title: { type: "string" },
    summary: { type: "string" },
    tags: {
      type: "array",
      items: { type: "string" },
    },
  },
  required: ["title", "summary", "tags"],
  additionalProperties: false,
};


const API_DEFAULT =
  (import.meta.env.VITE_API_URL as string | undefined)?.trim() ||
  "http://127.0.0.1:8000";


function App() {
  const [apiUrl, setApiUrl] = useState(
    localStorage.getItem("sg-api") || API_DEFAULT,
  );
  const [apiKey, setApiKey] = useState(
    localStorage.getItem("sg-key") || "",
  );
  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState<
    "playground" | "history"
  >("playground");

  const [prompt, setPrompt] = useState(
    "Create a concise overview of SchemaGuard AI, an AI reliability platform.",
  );
  const [schemaText, setSchemaText] = useState(
    JSON.stringify(DEFAULT_SCHEMA, null, 2),
  );
  const [provider, setProvider] = useState<Provider>("mock");
  const [retries, setRetries] = useState(2);

  const [result, setResult] = useState<Result | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [metrics, setMetrics] = useState<Metrics>({
    total_runs: 0,
    successful_runs: 0,
    failed_runs: 0,
    success_rate: 0,
    average_latency_ms: 0,
    average_attempts: 0,
  });

  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");

  const headers = useCallback(
    (json = false): HeadersInit => ({
      ...(json ? { "Content-Type": "application/json" } : {}),
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
    }),
    [apiKey],
  );

  const request = useCallback(
    async (path: string, init?: RequestInit) => {
      const response = await fetch(
        `${apiUrl.replace(/\/+$/, "")}${path}`,
        {
          ...init,
          headers: {
            ...headers(
              init?.body !== undefined,
            ),
            ...init?.headers,
          },
        },
      );

      if (!response.ok) {
        const body = await response.text();
        throw new Error(
          `API ${response.status}: ${body.slice(0, 500)}`,
        );
      }

      return response.json();
    },
    [apiUrl, headers],
  );

  const refreshDashboard = useCallback(async () => {
    try {
      const [health, history, stats] = await Promise.all([
        request("/api/health"),
        request("/api/runs?limit=20"),
        request("/api/metrics"),
      ]);

      setConnected(health.status === "ok");
      setRuns(history.runs ?? []);
      setMetrics(stats);
      setError("");
    } catch (err) {
      setConnected(false);
      setError(
        err instanceof Error
          ? err.message
          : "Could not connect to the backend.",
      );
    }
  }, [request]);

  useEffect(() => {
    void refreshDashboard();
  }, [refreshDashboard]);

  const saveSettings = () => {
    localStorage.setItem("sg-api", apiUrl);
    localStorage.setItem("sg-key", apiKey);
    setShowSettings(false);
    void refreshDashboard();
  };

  const runGeneration = async () => {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const parsedSchema = JSON.parse(schemaText);

      const response: Result = await request("/api/generate", {
        method: "POST",
        body: JSON.stringify({
          prompt,
          schema_name: "playground-schema",
          json_schema: parsedSchema,
          provider,
          max_retries: retries,
        }),
      });

      setResult(response);
      await refreshDashboard();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Generation failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  const copyOutput = async () => {
    if (result) {
      await navigator.clipboard.writeText(
        JSON.stringify(result, null, 2),
      );
    }
  };

  const successCount = metrics.successful_runs;
  const failedCount = metrics.failed_runs;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <ShieldCheck size={25} />
          </div>
          <div>
            <div className="brand-name">SchemaGuard</div>
            <div className="brand-caption">AI RELIABILITY PLATFORM</div>
          </div>
        </div>

        <div className="workspace-label">WORKSPACE</div>

        <button
          className="nav-item active"
          onClick={() => setActiveTab("playground")}
        >
          <LayoutDashboard size={18} />
          <span>Overview</span>
        </button>

        <button
          className={`nav-item ${
            activeTab === "history" ? "selected" : ""
          }`}
          onClick={() => setActiveTab("history")}
        >
          <Activity size={18} />
          <span>Run history</span>
        </button>

        <button
          className="nav-item"
          onClick={() => setShowSettings(true)}
        >
          <Settings2 size={18} />
          <span>Settings</span>
        </button>

        <div className="sidebar-bottom">
          <div className="connection-card">
            <span
              className={`status-dot ${
                connected ? "online" : ""
              }`}
            />
            <div>
              <strong>
                {connected ? "API connected" : "API disconnected"}
              </strong>
              <small>
                {connected
                  ? "Backend responding"
                  : "Check backend and URL"}
              </small>
            </div>
          </div>

          <div className="sidebar-footer">
            <ShieldCheck size={15} />
            <span>SchemaGuard AI · v1.0.0</span>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <span className="crumb-separator">/</span>
            <strong>
              {activeTab === "history"
                ? "Run history"
                : "Overview"}
            </strong>
          </div>

          <div className="topbar-actions">
            <span
              className={`connection-label ${
                connected ? "connected" : ""
              }`}
            >
              <span className="status-dot" />
              {connected ? "Connected" : "Disconnected"}
            </span>

            <button
              className="icon-button"
              title="Refresh dashboard"
              onClick={() => void refreshDashboard()}
            >
              <RefreshCw size={17} />
            </button>

            <button
              className="settings-button"
              onClick={() => setShowSettings(true)}
            >
              <Settings2 size={16} />
              Settings
            </button>
          </div>
        </header>

        <div className="page-content">
          <section className="page-heading">
            <div>
              <div className="eyebrow">
                <span className="eyebrow-line" />
                AI OBSERVABILITY & VALIDATION
              </div>

              <h1>
                {activeTab === "history"
                  ? "Execution history"
                  : "AI reliability dashboard"}
              </h1>

              <p>
                {activeTab === "history"
                  ? "Inspect previous generations and validation outcomes."
                  : "Validate structured outputs. Recover from errors. Build with confidence."}
              </p>
            </div>

            <div className="environment-pill">
              <span className="environment-dot" />
              DEVELOPMENT
              <ChevronDown size={14} />
            </div>
          </section>

          {error && (
            <div className="alert">
              <XCircle size={18} />
              <div>
                <strong>Request error</strong>
                <p>{error}</p>
              </div>
              <button
                className="icon-button"
                onClick={() => setError("")}
              >
                <XCircle size={16} />
              </button>
            </div>
          )}

          <section className="metrics-grid">
            <MetricCard
              icon={<Activity size={19} />}
              label="Total executions"
              value={metrics.total_runs}
              detail="Recorded runs"
              tone="blue"
            />

            <MetricCard
              icon={<CheckCircle2 size={19} />}
              label="Successful runs"
              value={successCount}
              detail={`${metrics.success_rate}% success rate`}
              tone="green"
            />

            <MetricCard
              icon={<XCircle size={19} />}
              label="Failed runs"
              value={failedCount}
              detail="Recovery exhausted or error"
              tone="red"
            />

            <MetricCard
              icon={<Clock3 size={19} />}
              label="Average latency"
              value={`${metrics.average_latency_ms} ms`}
              detail={`Avg. ${metrics.average_attempts} attempts`}
              tone="purple"
            />
          </section>

          {activeTab === "playground" ? (
            <>
              <section className="section-heading">
                <div>
                  <h2>Structured output playground</h2>
                  <p>
                    Define your contract and test an AI response.
                  </p>
                </div>
                <div className="live-tag">
                  <span className="status-dot online" />
                  LIVE WORKSPACE
                </div>
              </section>

              <section className="workspace-grid">
                <div className="panel editor-panel">
                  <div className="panel-header">
                    <div className="panel-title">
                      <div className="panel-icon blue-icon">
                        <Terminal size={17} />
                      </div>
                      <div>
                        <h3>Request configuration</h3>
                        <p>Configure input and validation rules</p>
                      </div>
                    </div>
                    <span className="step-number">01</span>
                  </div>

                  <div className="field-group">
                    <label htmlFor="prompt">
                      INPUT PROMPT
                    </label>
                    <textarea
                      id="prompt"
                      value={prompt}
                      onChange={(event) =>
                        setPrompt(event.target.value)
                      }
                      placeholder="Describe the output you need..."
                      rows={5}
                      maxLength={12000}
                    />
                    <div className="field-footnote">
                      <span>Natural language instructions</span>
                      <span>{prompt.length}/12000</span>
                    </div>
                  </div>

                  <div className="field-group">
                    <div className="field-label-row">
                      <label htmlFor="schema">
                        JSON SCHEMA
                      </label>
                      <span className="format-tag">
                        <FileJson size={12} />
                        JSON
                      </span>
                    </div>
                    <textarea
                      id="schema"
                      className="code-editor"
                      value={schemaText}
                      onChange={(event) =>
                        setSchemaText(event.target.value)
                      }
                      spellCheck={false}
                      rows={12}
                    />
                    <div className="field-footnote">
                      <span>
                        <ShieldCheck size={12} />
                        Validated by backend
                      </span>
                      <button
                        className="text-button"
                        onClick={() =>
                          setSchemaText(
                            JSON.stringify(
                              DEFAULT_SCHEMA,
                              null,
                              2,
                            ),
                          )
                        }
                      >
                        Reset schema
                      </button>
                    </div>
                  </div>

                  <div className="configuration-row">
                    <div className="field-group compact-field">
                      <label htmlFor="provider">
                        MODEL PROVIDER
                      </label>
                      <select
                        id="provider"
                        value={provider}
                        onChange={(event) =>
                          setProvider(
                            event.target.value as Provider,
                          )
                        }
                      >
                        <option value="mock">
                          Mock provider
                        </option>
                        <option value="openai_compatible">
                          OpenAI-compatible API
                        </option>
                      </select>
                    </div>

                    <div className="field-group compact-field">
                      <label htmlFor="retries">
                        MAX RETRIES
                      </label>
                      <select
                        id="retries"
                        value={retries}
                        onChange={(event) =>
                          setRetries(Number(event.target.value))
                        }
                      >
                        <option value={0}>0 retries</option>
                        <option value={1}>1 retry</option>
                        <option value={2}>2 retries</option>
                        <option value={3}>3 retries</option>
                        <option value={5}>5 retries</option>
                      </select>
                    </div>
                  </div>

                  <div className="execution-note">
                    <ShieldCheck size={17} />
                    <p>
                      Every successful result must pass JSON
                      Schema validation before it is accepted.
                    </p>
                  </div>

                  <button
                    className="run-button"
                    onClick={() => void runGeneration()}
                    disabled={
                      loading ||
                      !prompt.trim() ||
                      !connected
                    }
                  >
                    {loading ? (
                      <LoaderCircle
                        className="spin"
                        size={18}
                      />
                    ) : (
                      <Play size={17} />
                    )}
                    {loading
                      ? "Validating output..."
                      : "Run validation"}
                    {!loading && (
                      <ArrowUpRight size={16} />
                    )}
                  </button>

                  {!connected && (
                    <p className="help-text">
                      Start the FastAPI server to enable execution.
                    </p>
                  )}
                </div>

                <div className="right-column">
                  <div className="panel output-panel">
                    <div className="panel-header">
                      <div className="panel-title">
                        <div className="panel-icon green-icon">
                          <Code2 size={17} />
                        </div>
                        <div>
                          <h3>Execution result</h3>
                          <p>Validated structured response</p>
                        </div>
                      </div>

                      {result && (
                        <span
                          className={`result-badge ${
                            result.success ? "passed" : "failed"
                          }`}
                        >
                          {result.success ? "VALID" : "FAILED"}
                        </span>
                      )}
                    </div>

                    {result ? (
                      <>
                        <div className="result-summary">
                          <div>
                            <span>STATUS</span>
                            <strong
                              className={
                                result.success
                                  ? "success-text"
                                  : "failure-text"
                              }
                            >
                              {result.success
                                ? "Validation passed"
                                : "Validation failed"}
                            </strong>
                          </div>
                          <div>
                            <span>ATTEMPTS</span>
                            <strong>{result.attempts}</strong>
                          </div>
                          <div>
                            <span>LATENCY</span>
                            <strong>
                              {result.latency_ms} ms
                            </strong>
                          </div>
                        </div>

                        <div className="code-toolbar">
                          <span>
                            <span className="status-dot online" />
                            response.json
                          </span>
                          <button
                            className="icon-button"
                            title="Copy response"
                            onClick={() => void copyOutput()}
                          >
                            <Copy size={15} />
                          </button>
                        </div>

                        <pre className="output-code">
                          <code>
                            {JSON.stringify(
                              result.output,
                              null,
                              2,
                            )}
                          </code>
                        </pre>

                        {result.errors.length > 0 && (
                          <div className="validation-errors">
                            <strong>
                              Validation and recovery log
                            </strong>
                            {result.errors.map((item, index) => (
                              <p key={`${index}-${item}`}>
                                {item}
                              </p>
                            ))}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="empty-output">
                        <div className="empty-icon">
                          <Code2 size={27} />
                        </div>
                        <h3>No execution yet</h3>
                        <p>
                          Configure your schema and run a request
                          to inspect the validated output.
                        </p>
                        <div className="empty-checklist">
                          <span>
                            <CheckCircle2 size={15} />
                            Define a JSON contract
                          </span>
                          <span>
                            <CheckCircle2 size={15} />
                            Select an LLM provider
                          </span>
                          <span>
                            <CheckCircle2 size={15} />
                            Execute and validate
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="panel health-panel">
                    <div className="panel-header">
                      <div className="panel-title">
                        <div className="panel-icon purple-icon">
                          <Gauge size={17} />
                        </div>
                        <div>
                          <h3>System status</h3>
                          <p>Backend connectivity</p>
                        </div>
                      </div>
                    </div>

                    <div className="health-row">
                      <span>
                        <span
                          className={`status-dot ${
                            connected ? "online" : ""
                          }`}
                        />
                        FastAPI backend
                      </span>
                      <strong>
                        {connected ? "Operational" : "Offline"}
                      </strong>
                    </div>

                    <div className="health-row">
                      <span>
                        <Database size={15} />
                        Run history
                      </span>
                      <strong>
                        {metrics.total_runs} records
                      </strong>
                    </div>

                    <div className="health-row">
                      <span>
                        <ShieldCheck size={15} />
                        Validation engine
                      </span>
                      <strong>Server-side</strong>
                    </div>
                  </div>
                </div>
              </section>

              <section className="panel recent-panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <div className="panel-icon blue-icon">
                      <Activity size={17} />
                    </div>
                    <div>
                      <h3>Recent executions</h3>
                      <p>Your latest validation requests</p>
                    </div>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => setActiveTab("history")}
                  >
                    View all <ArrowUpRight size={14} />
                  </button>
                </div>

                <RunTable runs={runs.slice(0, 5)} />
              </section>
            </>
          ) : (
            <section className="panel recent-panel history-panel">
              <div className="panel-header">
                <div className="panel-title">
                  <div className="panel-icon blue-icon">
                    <Activity size={17} />
                  </div>
                  <div>
                    <h3>All executions</h3>
                    <p>
                      Showing the latest {runs.length} recorded runs
                    </p>
                  </div>
                </div>
                <button
                  className="icon-button"
                  onClick={() => void refreshDashboard()}
                  title="Refresh history"
                >
                  <RefreshCw size={16} />
                </button>
              </div>
              <RunTable runs={runs} />
            </section>
          )}

          <footer className="page-footer">
            <span>
              <ShieldCheck size={15} />
              SchemaGuard AI
            </span>
            <span>Structured outputs. Predictable systems.</span>
          </footer>
        </div>
      </main>

      {showSettings && (
        <div
          className="modal-backdrop"
          onClick={() => setShowSettings(false)}
        >
          <section
            className="settings-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-heading">
              <div>
                <h2>Workspace settings</h2>
                <p>Configure your local API connection.</p>
              </div>
              <button
                className="icon-button"
                onClick={() => setShowSettings(false)}
              >
                <XCircle size={19} />
              </button>
            </div>

            <div className="field-group">
              <label htmlFor="api-url">BACKEND URL</label>
              <input
                id="api-url"
                value={apiUrl}
                onChange={(event) =>
                  setApiUrl(event.target.value)
                }
                placeholder="http://127.0.0.1:8000"
              />
            </div>

            <div className="field-group">
              <label htmlFor="api-key">
                <KeyRound size={13} />
                API KEY
              </label>
              <input
                id="api-key"
                type="password"
                value={apiKey}
                onChange={(event) =>
                  setApiKey(event.target.value)
                }
                placeholder="Optional in local development"
                autoComplete="off"
              />
              <span className="help-text">
                A browser-stored key is convenient for development,
                but use secure server-side sessions for a public
                production application.
              </span>
            </div>

            <div className="modal-actions">
              <button
                className="settings-button"
                onClick={() => setShowSettings(false)}
              >
                Cancel
              </button>
              <button
                className="run-button save-button"
                onClick={saveSettings}
              >
                Save and reconnect
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  detail,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  detail: string;
  tone: string;
}) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <div className={`metric-icon ${tone}`}>{icon}</div>
        <span className="metric-indicator">
          <Activity size={13} />
        </span>
      </div>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-detail">{detail}</div>
    </article>
  );
}

function RunTable({ runs }: { runs: Run[] }) {
  if (runs.length === 0) {
    return (
      <div className="table-empty">
        <FlaskConical size={22} />
        <p>No runs recorded yet. Execute your first request.</p>
      </div>
    );
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>RUN ID</th>
            <th>PROVIDER</th>
            <th>SCHEMA</th>
            <th>STATUS</th>
            <th>ATTEMPTS</th>
            <th>LATENCY</th>
            <th>TIME</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td>
                <span className="run-id">
                  #{String(run.id).padStart(4, "0")}
                </span>
              </td>
              <td>
                <span className="provider-cell">
                  <span className="provider-dot" />
                  {run.provider}
                </span>
              </td>
              <td>{run.schema_name}</td>
              <td>
                <span
                  className={`result-badge ${
                    run.success ? "passed" : "failed"
                  }`}
                >
                  {run.success ? (
                    <CheckCircle2 size={12} />
                  ) : (
                    <XCircle size={12} />
                  )}
                  {run.success ? "Passed" : "Failed"}
                </span>
              </td>
              <td>{run.attempts}</td>
              <td>{run.latency_ms} ms</td>
              <td>
                {new Date(run.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;