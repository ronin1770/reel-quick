"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

type CustomVoiceRecord = {
  request_id: string;
  voice_name?: string;
  instructions?: string;
  custom_voice_text?: string;
  output_file_location?: string;
  created_at?: string;
  updated_at?: string;
};

type CustomVoiceStatusResponse = {
  request_id: string;
  status: string;
  custom_voice_available: boolean;
  error_code?: string | null;
  error_message?: string | null;
};

type CustomVoiceDetailResponse = {
  custom_voice?: CustomVoiceRecord;
  sound_design_prompt?: Record<string, unknown> | null;
};

const API_BASE_ENV = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

const resolveApiBase = () => {
  if (API_BASE_ENV) {
    return API_BASE_ENV;
  }
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://127.0.0.1:8000";
};

const toPrettyJson = (value: unknown) => {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value ?? "");
  }
};

const normalizeStatus = (status?: string) =>
  (status ?? "unknown").toLowerCase();

const statusClass = (status?: string) => {
  const normalized = normalizeStatus(status);
  if (normalized === "completed") return "text-emerald-200";
  if (normalized === "failed") return "text-rose-200";
  if (normalized === "in_progress") return "text-sky-200";
  if (normalized === "not_found") return "text-amber-200";
  return "text-soft";
};

const statusLabel = (status?: string) => {
  const normalized = normalizeStatus(status);
  if (normalized === "in_progress") return "In Progress";
  if (normalized === "completed") return "Completed";
  if (normalized === "failed") return "Failed";
  if (normalized === "not_found") return "Not Found";
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
};

export default function CustomVoicesLibrary() {
  const apiBase = useMemo(resolveApiBase, []);
  const searchParams = useSearchParams();
  const requestedId = (searchParams.get("request_id") ?? "").trim();

  const [voices, setVoices] = useState<CustomVoiceRecord[]>([]);
  const [selectedRequestId, setSelectedRequestId] = useState<string>("");
  const [selectedVoice, setSelectedVoice] = useState<CustomVoiceRecord | null>(null);
  const [soundDesignPrompt, setSoundDesignPrompt] = useState<Record<string, unknown> | null>(
    null
  );
  const [statusInfo, setStatusInfo] = useState<CustomVoiceStatusResponse | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchVoices = useCallback(async () => {
    setIsLoadingList(true);
    setError(null);
    try {
      const response = await fetch(`${apiBase}/custom-voices`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Unable to load custom voices (${response.status}).`);
      }
      const data = (await response.json()) as CustomVoiceRecord[];
      const rows = Array.isArray(data) ? data : [];
      setVoices(rows);
      return rows;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load custom voices.");
      return [];
    } finally {
      setIsLoadingList(false);
    }
  }, [apiBase]);

  const fetchVoiceDetails = useCallback(
    async (requestId: string) => {
      if (!requestId) {
        setSelectedVoice(null);
        setSoundDesignPrompt(null);
        return;
      }

      setIsLoadingDetails(true);
      setError(null);
      try {
        const response = await fetch(
          `${apiBase}/custom-voices/${encodeURIComponent(requestId)}`,
          { cache: "no-store" }
        );
        if (!response.ok) {
          throw new Error(`Unable to load custom voice details (${response.status}).`);
        }
        const data = (await response.json()) as CustomVoiceDetailResponse;
        setSelectedVoice(data.custom_voice ?? null);
        setSoundDesignPrompt(
          data.sound_design_prompt && typeof data.sound_design_prompt === "object"
            ? data.sound_design_prompt
            : null
        );
      } catch (err) {
        setSelectedVoice(null);
        setSoundDesignPrompt(null);
        setError(
          err instanceof Error ? err.message : "Unable to load custom voice details."
        );
      } finally {
        setIsLoadingDetails(false);
      }
    },
    [apiBase]
  );

  const fetchStatus = useCallback(
    async (requestId: string): Promise<CustomVoiceStatusResponse | null> => {
      if (!requestId) return null;
      try {
        const response = await fetch(
          `${apiBase}/custom-voices/status/${encodeURIComponent(requestId)}`,
          { cache: "no-store" }
        );
        if (!response.ok) {
          return null;
        }
        const data = (await response.json()) as CustomVoiceStatusResponse;
        setStatusInfo(data);
        return data;
      } catch {
        return null;
      }
    },
    [apiBase]
  );

  useEffect(() => {
    const initialize = async () => {
      const rows = await fetchVoices();
      if (requestedId) {
        setSelectedRequestId(requestedId);
        return;
      }
      if (rows.length > 0) {
        setSelectedRequestId(rows[0].request_id);
      }
    };
    void initialize();
  }, [fetchVoices, requestedId]);

  useEffect(() => {
    if (!requestedId) {
      return;
    }

    let active = true;
    let timer: number | undefined;

    const poll = async () => {
      const status = await fetchStatus(requestedId);
      if (!active || !status) {
        return;
      }

      if (status.status === "completed") {
        const rows = await fetchVoices();
        if (!active) return;
        setSelectedRequestId(requestedId);
        if (!rows.some((row) => row.request_id === requestedId)) {
          return;
        }
        await fetchVoiceDetails(requestedId);
        return;
      }

      if (status.status === "failed" || status.status === "not_found") {
        return;
      }

      timer = window.setTimeout(() => {
        void poll();
      }, 3000);
    };

    void poll();
    return () => {
      active = false;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [fetchStatus, fetchVoices, fetchVoiceDetails, requestedId]);

  useEffect(() => {
    if (!selectedRequestId) {
      setSelectedVoice(null);
      setSoundDesignPrompt(null);
      return;
    }
    if (!voices.some((row) => row.request_id === selectedRequestId)) {
      setSelectedVoice(null);
      setSoundDesignPrompt(null);
      return;
    }
    void fetchVoiceDetails(selectedRequestId);
  }, [fetchVoiceDetails, selectedRequestId, voices]);

  const promptParametersText = useMemo(() => {
    if (!soundDesignPrompt) {
      return "";
    }
    const payload = {
      sound_design_id: soundDesignPrompt.sound_design_id,
      status: soundDesignPrompt.status,
      request_payload: soundDesignPrompt.request_payload,
    };
    return toPrettyJson(payload);
  }, [soundDesignPrompt]);

  const selectedAudioUrl = useMemo(() => {
    if (!selectedVoice?.request_id) return "";
    return `${apiBase}/custom-voices/${encodeURIComponent(selectedVoice.request_id)}/audio`;
  }, [apiBase, selectedVoice?.request_id]);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <section className="neon-panel rounded-3xl p-6 md:p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <span className="neon-pill">Voice library</span>
            <h1 className="font-display text-3xl font-semibold sm:text-4xl">
              Custom Voices
            </h1>
            <p className="text-muted">
              Select a generated custom voice and inspect the original design parameters.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {statusInfo ? (
              <span
                className={`neon-badge text-[10px] font-semibold uppercase tracking-[0.25em] ${statusClass(
                  statusInfo.status
                )}`}
              >
                {statusLabel(statusInfo.status)}
              </span>
            ) : null}
            <button
              className="neon-button neon-button-ghost"
              onClick={() => {
                void fetchVoices();
                if (requestedId) {
                  void fetchStatus(requestedId);
                }
              }}
              type="button"
            >
              {isLoadingList ? "Refreshing..." : "Refresh"}
            </button>
            <Link className="neon-button neon-button-primary" href="/sound-designer">
              Back To Designer
            </Link>
          </div>
        </div>

        {error ? (
          <div className="mt-4 rounded-2xl border border-rose-400/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        ) : null}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <article className="neon-panel rounded-3xl p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-soft">
            Selection
          </p>

          <label className="mt-4 block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-soft">
              Custom Voice
            </span>
            <select
              className="neon-input"
              value={selectedRequestId}
              onChange={(event) => setSelectedRequestId(event.target.value)}
            >
              <option value="">Select custom voice</option>
              {voices.map((voice) => (
                <option key={voice.request_id} value={voice.request_id}>
                  {voice.voice_name || voice.request_id}
                </option>
              ))}
            </select>
          </label>

          <label className="mt-4 block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-soft">
              Audio Path
            </span>
            <input
              className="neon-input"
              readOnly
              value={selectedVoice?.output_file_location ?? ""}
            />
          </label>

          <label className="mt-4 block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-soft">
              Voice Name
            </span>
            <input
              className="neon-input"
              readOnly
              value={selectedVoice?.voice_name ?? ""}
            />
          </label>

          <label className="mt-4 block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-soft">
              Instructions
            </span>
            <textarea
              className="neon-input neon-textarea"
              readOnly
              value={selectedVoice?.instructions ?? ""}
            />
          </label>

          <label className="mt-4 block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-soft">
              Custom Voice Text
            </span>
            <textarea
              className="neon-input neon-textarea"
              readOnly
              value={selectedVoice?.custom_voice_text ?? ""}
            />
          </label>
        </article>

        <article className="neon-panel rounded-3xl p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-soft">
            Sound Design Prompt
          </p>

          <label className="mt-4 block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-soft">
              Parameters (Read-only)
            </span>
            <textarea
              className="neon-input neon-textarea"
              readOnly
              value={promptParametersText}
            />
          </label>

          <div className="mt-6 space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-soft">
              Audio Preview
            </span>
            {selectedAudioUrl ? (
              <audio className="w-full" controls src={selectedAudioUrl} />
            ) : (
              <p className="text-sm text-soft">
                {isLoadingDetails
                  ? "Loading selected voice..."
                  : "Select a custom voice to enable audio preview."}
              </p>
            )}
          </div>
        </article>
      </section>
    </div>
  );
}
