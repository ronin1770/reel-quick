"use client";

import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from "react";

type VoiceCloneJob = {
  job_id: string;
  ref_audio_path: string;
  ref_text: string;
  status?: string;
  result_path?: string | null;
  error_reason?: string | null;
  created_at?: string;
  updated_at?: string;
};

type UploadResponse = {
  file_location?: string;
};

type EnqueueResponse = {
  message: string;
  voice_clone_job_id: string;
  status: string;
};

const API_BASE_ENV = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
const PAGE_SIZE = 5;

const normalizeStatus = (status?: string) => (status ?? "queued").toLowerCase();

const statusLabel = (status?: string) => {
  const normalized = normalizeStatus(status);
  if (normalized === "queued") return "Queued";
  if (normalized === "processing") return "Processing";
  if (normalized === "completed") return "Completed";
  if (normalized === "failed") return "Failed";
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
};

const statusClass = (status?: string) => {
  const normalized = normalizeStatus(status);
  if (normalized === "completed") return "text-emerald-200";
  if (normalized === "failed") return "text-rose-200";
  if (normalized === "processing") return "text-sky-200";
  return "text-indigo-200";
};

const fileNameFromPath = (path: string) => {
  const normalized = path.replaceAll("\\", "/");
  const name = normalized.split("/").pop() ?? normalized;
  return name || "Unknown";
};

const getErrorMessage = async (response: Response) => {
  try {
    const data = await response.json();
    if (typeof data?.detail === "string") {
      return data.detail;
    }
    if (Array.isArray(data?.detail)) {
      return data.detail
        .map((item: { msg?: string }) => item?.msg)
        .filter(Boolean)
        .join(", ");
    }
  } catch {
    return null;
  }
  return null;
};

const resolveApiBase = () => {
  if (API_BASE_ENV) {
    return API_BASE_ENV;
  }
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://127.0.0.1:8000";
};

const getNetworkErrorMessage = (error: unknown, apiBase: string, action: string) => {
  if (error instanceof TypeError) {
    return `Network error while ${action}. Unable to reach API at ${apiBase}. Configure NEXT_PUBLIC_API_BASE_URL if backend runs on a different host/port.`;
  }
  return null;
};

export default function VoiceCloner() {
  const apiBase = useMemo(resolveApiBase, []);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedAudioPath, setUploadedAudioPath] = useState<string | null>(null);
  const [referenceText, setReferenceText] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const [jobs, setJobs] = useState<VoiceCloneJob[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalJobs, setTotalJobs] = useState(0);

  const fetchJobs = useCallback(async (targetPage: number) => {
    setIsLoadingJobs(true);
    setJobsError(null);

    try {
      const url = new URL("/voice-clones", apiBase);
      url.searchParams.set("page", String(targetPage));
      url.searchParams.set("page_size", String(PAGE_SIZE));

      const response = await fetch(url.toString(), { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Unable to load voice clone jobs (${response.status}).`);
      }
      const data = (await response.json()) as VoiceCloneJob[];
      const totalCountHeader = response.headers.get("x-total-count");
      const parsedTotal = totalCountHeader
        ? Number.parseInt(totalCountHeader, 10)
        : Number.NaN;

      setJobs(Array.isArray(data) ? data : []);
      setTotalJobs(Number.isFinite(parsedTotal) ? parsedTotal : data.length);
      setPage(targetPage);
    } catch (error) {
      const networkError = getNetworkErrorMessage(error, apiBase, "loading voice clone jobs");
      if (networkError) {
        setJobsError(networkError);
        return;
      }
      setJobsError(
        error instanceof Error ? error.message : "Unable to load voice clone jobs."
      );
    } finally {
      setIsLoadingJobs(false);
    }
  }, [apiBase]);

  useEffect(() => {
    fetchJobs(1);
  }, [fetchJobs]);

  const hasInFlightJobs = useMemo(
    () => jobs.some((job) => ["queued", "processing"].includes(normalizeStatus(job.status))),
    [jobs]
  );

  useEffect(() => {
    if (!hasInFlightJobs) return;

    const timer = window.setInterval(() => {
      fetchJobs(page);
    }, 4000);

    return () => window.clearInterval(timer);
  }, [fetchJobs, hasInFlightJobs, page]);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setUploadedAudioPath(null);
    setFormError(null);
    setStatusMessage(null);
  };

  const uploadReferenceAudio = async (): Promise<string | null> => {
    if (!selectedFile) {
      setFormError("Please choose a WAV file first.");
      return null;
    }

    const looksLikeWav =
      selectedFile.name.toLowerCase().endsWith(".wav") ||
      selectedFile.type.toLowerCase().includes("wav");
    if (!looksLikeWav) {
      setFormError("Only WAV files are supported for voice cloning.");
      return null;
    }

    setIsUploading(true);
    setFormError(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(`${apiBase}/uploads`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const detail = await getErrorMessage(response);
        throw new Error(detail ?? `Audio upload failed (${response.status})`);
      }

      const data = (await response.json()) as UploadResponse;
      if (!data.file_location) {
        throw new Error("Upload succeeded without a file_location.");
      }

      setUploadedAudioPath(data.file_location);
      setStatusMessage(
        `Reference audio uploaded: ${fileNameFromPath(data.file_location)}`
      );
      return data.file_location;
    } catch (error) {
      const networkError = getNetworkErrorMessage(
        error,
        apiBase,
        "uploading reference audio"
      );
      if (networkError) {
        setFormError(networkError);
        return null;
      }
      setFormError(
        error instanceof Error ? error.message : "Unable to upload reference audio."
      );
      return null;
    } finally {
      setIsUploading(false);
    }
  };

  const handleUploadReferenceAudio = async () => {
    setFormError(null);
    setStatusMessage(null);
    await uploadReferenceAudio();
  };

  const handleClone = async () => {
    setFormError(null);
    setStatusMessage(null);

    const text = referenceText.trim();
    if (!text) {
      setFormError("Reference text is required.");
      return;
    }

    let audioPath = uploadedAudioPath;
    if (!audioPath) {
      audioPath = await uploadReferenceAudio();
      if (!audioPath) {
        return;
      }
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`${apiBase}/voice-clones/enqueue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ref_audio_path: audioPath,
          ref_text: text,
        }),
      });
      if (!response.ok) {
        const detail = await getErrorMessage(response);
        throw new Error(detail ?? `Unable to queue voice clone (${response.status})`);
      }

      const data = (await response.json()) as EnqueueResponse;
      setStatusMessage(
        `Voice clone queued successfully. Job ID: ${data.voice_clone_job_id}`
      );
      await fetchJobs(1);
    } catch (error) {
      const networkError = getNetworkErrorMessage(error, apiBase, "queueing voice clone");
      if (networkError) {
        setFormError(networkError);
        return;
      }
      setFormError(
        error instanceof Error ? error.message : "Unable to queue voice clone."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalJobs / PAGE_SIZE));
  const canGoPrev = page > 1;
  const canGoNext = page < totalPages;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <section className="neon-panel rounded-3xl p-6 md:p-8">
        <div className="space-y-3">
          <span className="neon-pill">Voice studio</span>
          <h1 className="font-display text-3xl font-semibold sm:text-4xl">
            Voice Cloner
          </h1>
          <p className="text-sm text-muted">
            Upload a reference WAV, provide transcript text, then queue a clone job.
          </p>
        </div>

        <div className="mt-8 grid gap-5">
          <div className="grid gap-3 md:grid-cols-[180px_minmax(0,1fr)_120px] md:items-center">
            <label className="text-sm font-semibold text-soft">Reference Audio</label>
            <input
              accept=".wav,audio/wav"
              className="neon-input"
              onChange={handleFileChange}
              type="file"
            />
            <button
              className="neon-button neon-button-ghost w-full"
              type="button"
              onClick={handleUploadReferenceAudio}
              disabled={isUploading || !selectedFile}
            >
              {isUploading ? "Uploading..." : uploadedAudioPath ? "Re-upload" : "Upload"}
            </button>
          </div>

          <div className="grid gap-3 md:grid-cols-[180px_minmax(0,1fr)] md:items-start">
            <label className="pt-3 text-sm font-semibold text-soft">Reference Text</label>
            <textarea
              className="neon-input neon-textarea"
              onChange={(event) => setReferenceText(event.target.value)}
              placeholder="Type the exact transcript spoken in reference audio..."
              value={referenceText}
            />
          </div>
        </div>

        {uploadedAudioPath && (
          <p className="mt-4 text-xs text-soft">
            Uploaded path: <span className="font-mono">{uploadedAudioPath}</span>
          </p>
        )}

        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            className="neon-button neon-button-primary"
            type="button"
            onClick={handleClone}
            disabled={isSubmitting || isUploading}
          >
            {isSubmitting ? "Queueing..." : "Clone"}
          </button>
        </div>

        {statusMessage && (
          <p className="mt-4 rounded-2xl border border-emerald-300/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
            {statusMessage}
          </p>
        )}
        {formError && (
          <p className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            {formError}
          </p>
        )}
      </section>

      <div className="neon-divider" />

      <section className="neon-panel rounded-3xl p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-soft">
              Voice clone jobs
            </p>
            <p className="text-xs text-muted">
              Filename, status, and output download for completed jobs.
            </p>
          </div>
          <button
            className="neon-button neon-button-ghost"
            type="button"
            onClick={() => fetchJobs(page)}
            disabled={isLoadingJobs}
          >
            {isLoadingJobs ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        {jobsError && (
          <p className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            {jobsError}
          </p>
        )}

        <div className="mt-5 overflow-x-auto">
          {jobs.length === 0 ? (
            <p className="text-sm text-soft">
              {isLoadingJobs ? "Loading voice clone jobs..." : "No voice clone jobs yet."}
            </p>
          ) : (
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-white/10 text-xs uppercase tracking-[0.3em] text-soft">
                <tr>
                  <th className="py-3 pr-6">Filename</th>
                  <th className="py-3 pr-6">Status</th>
                  <th className="py-3 pr-6">Download Link</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.job_id}
                    className="border-b border-white/10 last:border-b-0"
                  >
                    <td className="py-4 pr-6 align-top">
                      <p className="font-semibold">
                        {fileNameFromPath(job.ref_audio_path)}
                      </p>
                      <p className="mt-1 text-xs text-soft font-mono">{job.job_id}</p>
                    </td>
                    <td className="py-4 pr-6 align-top">
                      <p className={`font-semibold ${statusClass(job.status)}`}>
                        {statusLabel(job.status)}
                      </p>
                      {job.error_reason && (
                        <p className="mt-1 max-w-[280px] text-xs text-rose-200">
                          {job.error_reason}
                        </p>
                      )}
                    </td>
                    <td className="py-4 align-top">
                      {normalizeStatus(job.status) === "completed" ? (
                        <a
                          className="text-sm font-semibold text-cyan-200 underline-offset-4 hover:underline"
                          href={`${apiBase}/voice-clones/${job.job_id}/download`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Download
                        </a>
                      ) : (
                        <span className="text-xs text-soft">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="mt-6 flex items-center justify-between gap-3">
          <button
            className="neon-button neon-button-ghost min-w-[120px]"
            type="button"
            disabled={!canGoPrev || isLoadingJobs}
            onClick={() => fetchJobs(page - 1)}
          >
            Previous
          </button>
          <p className="text-sm text-soft">
            {page} of {totalPages} pages
          </p>
          <button
            className="neon-button neon-button-ghost min-w-[120px]"
            type="button"
            disabled={!canGoNext || isLoadingJobs}
            onClick={() => fetchJobs(page + 1)}
          >
            Next
          </button>
        </div>
      </section>
    </div>
  );
}
