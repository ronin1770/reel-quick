"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type WorkerStatus = {
  key: string;
  name: string;
  settings_path: string;
  running: boolean;
  pid: number | null;
  started_at: string | null;
};

type WorkersListResponse = {
  workers: WorkerStatus[];
};

type WorkerActionResponse = {
  message: string;
  worker: WorkerStatus;
};

type WorkerErrorLogResponse = {
  logs: string[];
};

const API_BASE_ENV = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

const resolveApiBase = () => {
  if (API_BASE_ENV) {
    return API_BASE_ENV;
  }
  return "http://127.0.0.1:8000";
};

const parseJsonSafely = async <T,>(response: Response): Promise<T | null> => {
  try {
    return (await response.json()) as T;
  } catch {
    return null;
  }
};

const parseErrorDetail = (payload: unknown) => {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) {
    return null;
  }
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  return null;
};

const formatStartedAt = (startedAt: string | null) => {
  if (!startedAt) {
    return "N/A";
  }
  const parsed = new Date(startedAt);
  if (Number.isNaN(parsed.getTime())) {
    return startedAt;
  }
  return parsed.toLocaleString();
};

export default function WorkerControlPanel() {
  const apiBase = useMemo(resolveApiBase, []);
  const [workers, setWorkers] = useState<WorkerStatus[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyWorkers, setBusyWorkers] = useState<Record<string, boolean>>({});

  const fetchWorkers = useCallback(
    async (silent = false) => {
      if (!silent) {
        setRefreshing(true);
      }

      try {
        const response = await fetch(`${apiBase}/api/v1/control-panel/workers`, {
          cache: "no-store",
        });
        const payload = await parseJsonSafely<WorkersListResponse>(response);

        if (!response.ok || !payload || !Array.isArray(payload.workers)) {
          const detail = parseErrorDetail(payload);
          throw new Error(detail ?? "Unable to load workers.");
        }

        setWorkers(payload.workers);
      } catch (fetchError) {
        if (fetchError instanceof TypeError) {
          setError(`Unable to reach API at ${apiBase}.`);
        } else if (fetchError instanceof Error) {
          setError(fetchError.message);
        } else {
          setError("Unable to load workers.");
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [apiBase]
  );

  const fetchErrorLogs = useCallback(async () => {
    try {
      const response = await fetch(`${apiBase}/api/v1/control-panel/error-log`, {
        cache: "no-store",
      });
      const payload = await parseJsonSafely<WorkerErrorLogResponse>(response);
      if (!response.ok || !payload || !Array.isArray(payload.logs)) {
        return;
      }
      setLogs(payload.logs);
    } catch {
      setLogs([]);
    }
  }, [apiBase]);

  useEffect(() => {
    void fetchWorkers();
    void fetchErrorLogs();

    const timer = window.setInterval(() => {
      void fetchWorkers(true);
    }, 5000);

    return () => {
      window.clearInterval(timer);
    };
  }, [fetchWorkers, fetchErrorLogs]);

  const setWorkerBusy = (workerKey: string, isBusy: boolean) => {
    setBusyWorkers((previous) => ({
      ...previous,
      [workerKey]: isBusy,
    }));
  };

  const toggleWorker = async (worker: WorkerStatus) => {
    const nextAction = worker.running ? "stop" : "start";
    setError(null);
    setFeedback(null);
    setWorkerBusy(worker.key, true);

    try {
      const response = await fetch(
        `${apiBase}/api/v1/control-panel/workers/${worker.key}/${nextAction}`,
        {
          method: "POST",
        }
      );
      const payload = await parseJsonSafely<WorkerActionResponse>(response);

      if (!response.ok || !payload || !payload.worker) {
        const detail = parseErrorDetail(payload);
        throw new Error(detail ?? `Unable to ${nextAction} worker.`);
      }

      setWorkers((previous) =>
        previous.map((current) =>
          current.key === payload.worker.key ? payload.worker : current
        )
      );
      setFeedback(payload.message);
      void fetchWorkers(true);
    } catch (actionError) {
      if (actionError instanceof Error) {
        setError(actionError.message);
      } else {
        setError(`Unable to ${nextAction} worker.`);
      }
    } finally {
      setWorkerBusy(worker.key, false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <section className="neon-panel rounded-3xl p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-soft">
              Operations
            </p>
            <h1 className="font-display text-3xl font-semibold sm:text-4xl">
              Worker Control Panel
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-muted sm:text-base">
              FastAPI and frontend are expected to auto-start. Use this panel to
              turn ARQ workers on and off.
            </p>
          </div>
          <button
            className="neon-button neon-button-ghost"
            disabled={refreshing}
            onClick={() => {
              void fetchWorkers();
              void fetchErrorLogs();
            }}
            type="button"
          >
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        {feedback ? <p className="alert alert-success mt-4">{feedback}</p> : null}

        {error ? <p className="alert alert-error mt-4">{error}</p> : null}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="neon-card rounded-3xl p-6 sm:p-7">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-2xl font-semibold">Workers</h2>
            <span className="text-xs font-semibold uppercase tracking-[0.25em] text-soft">
              {workers.length} total
            </span>
          </div>

          {loading ? (
            <p className="mt-5 text-sm text-muted">Loading worker statuses...</p>
          ) : (
            <div className="mt-5 space-y-4">
              {workers.map((worker) => {
                const isBusy = Boolean(busyWorkers[worker.key]);
                return (
                  <article className="surface-subtle rounded-2xl p-4" key={worker.key}>
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div>
                        <p className="text-base font-semibold">{worker.name}</p>
                        <p className="mt-1 text-xs text-muted">
                          {worker.settings_path}
                        </p>
                        <p className="mt-2 text-xs text-soft">
                          PID: {worker.pid ?? "N/A"} | Started: {formatStartedAt(worker.started_at)}
                        </p>
                      </div>

                      <div className="flex items-center gap-3">
                        <span
                          className={`text-sm font-semibold ${
                            worker.running
                              ? "text-status-success"
                              : "text-status-neutral"
                          }`}
                        >
                          {worker.running ? "ON" : "OFF"}
                        </span>
                        <button
                          aria-checked={worker.running}
                          aria-label={`${worker.running ? "Stop" : "Start"} ${worker.name}`}
                          className={`toggle-switch relative inline-flex h-8 w-16 items-center rounded-full transition ${
                            isBusy ? "cursor-not-allowed opacity-60" : ""
                          }`}
                          data-on={worker.running}
                          disabled={isBusy}
                          onClick={() => {
                            void toggleWorker(worker);
                          }}
                          role="switch"
                          type="button"
                        >
                          <span
                            className={`toggle-thumb inline-block h-6 w-6 transform rounded-full transition-transform ${
                              worker.running ? "translate-x-8" : "translate-x-1"
                            }`}
                          />
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>

        <div className="neon-card rounded-3xl p-6 sm:p-7">
          <h2 className="font-display text-2xl font-semibold">Error Log</h2>
          <p className="mt-2 text-sm text-muted">
            Placeholder panel. Log ingestion will be added later.
          </p>

          <div className="surface-subtle mt-5 rounded-2xl p-4">
            {logs.length > 0 ? (
              <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs text-status-error">
                {logs.join("\n")}
              </pre>
            ) : (
              <p className="text-sm text-soft">No error logs yet.</p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
