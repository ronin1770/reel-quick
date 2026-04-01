"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type CreateTextOverlayPageProps = {
  videoId: string;
};

type VideoRecord = {
  video_id: string;
  video_title: string;
  video_size?: string | null;
  status?: string;
  output_file_location?: string | null;
};

type TextOverlay = {
  id: string;
  text: string;
  startSeconds: number;
  endSeconds: number;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const parseDurationToSeconds = (value?: string | null): number => {
  if (!value) return 0;
  const trimmed = value.trim();
  if (!trimmed) return 0;

  const numeric = Number(trimmed);
  if (Number.isFinite(numeric) && numeric > 0) {
    return Math.floor(numeric);
  }

  const parts = trimmed.split(":").map((part) => Number(part));
  if (parts.length < 2 || parts.some((part) => !Number.isFinite(part))) {
    return 0;
  }

  let multiplier = 1;
  let total = 0;
  for (let index = parts.length - 1; index >= 0; index -= 1) {
    total += parts[index] * multiplier;
    multiplier *= 60;
  }

  return total > 0 ? Math.floor(total) : 0;
};

const formatClock = (value: number) => {
  const safe = Math.max(0, Math.floor(value));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
};

const fileNameFromPath = (value: string) => {
  const normalized = value.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  return parts.at(-1) ?? value;
};

export default function CreateTextOverlayPage({
  videoId,
}: CreateTextOverlayPageProps) {
  const [video, setVideo] = useState<VideoRecord | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [overlays, setOverlays] = useState<TextOverlay[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [draftText, setDraftText] = useState("");
  const [draftStart, setDraftStart] = useState(0);
  const [draftEnd, setDraftEnd] = useState(1);
  const [uiNote, setUiNote] = useState<string | null>(null);

  const fetchVideo = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE}/videos/${encodeURIComponent(videoId)}`,
        {
          cache: "no-store",
        }
      );
      if (!response.ok) {
        throw new Error(`Unable to load video (${response.status})`);
      }
      const data = (await response.json()) as VideoRecord;
      setVideo(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load video.");
      setVideo(null);
    } finally {
      setIsLoading(false);
    }
  }, [videoId]);

  useEffect(() => {
    fetchVideo();
  }, [fetchVideo]);

  const videoDuration = useMemo(
    () => parseDurationToSeconds(video?.video_size),
    [video?.video_size]
  );

  const canAddOverlay = videoDuration >= 1;
  const maxStart = Math.max(0, videoDuration - 1);
  const minEnd = Math.min(videoDuration, draftStart + 1);
  const videoDownloadUrl =
    video?.video_id && String(video.status ?? "").toLowerCase() === "completed"
      ? `${API_BASE}/videos/${encodeURIComponent(video.video_id)}/download`
      : null;

  const openOverlayDialog = () => {
    if (!canAddOverlay) return;
    setDraftText("");
    setDraftStart(0);
    setDraftEnd(Math.max(1, Math.min(videoDuration, 3)));
    setUiNote(null);
    setIsDialogOpen(true);
  };

  const closeOverlayDialog = () => {
    setIsDialogOpen(false);
  };

  const onStartChange = (raw: number) => {
    const clampedStart = Math.max(0, Math.min(raw, maxStart));
    setDraftStart(clampedStart);
    setDraftEnd((previous) => {
      if (previous <= clampedStart) {
        return Math.min(videoDuration, clampedStart + 1);
      }
      return previous;
    });
  };

  const onEndChange = (raw: number) => {
    const clampedEnd = Math.max(minEnd, Math.min(raw, videoDuration));
    setDraftEnd(clampedEnd);
  };

  const canCreateDraft =
    draftText.trim().length > 0 &&
    draftEnd > draftStart &&
    draftEnd <= videoDuration;

  const addOverlay = () => {
    if (!canCreateDraft) return;
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const overlay: TextOverlay = {
      id,
      text: draftText.trim(),
      startSeconds: draftStart,
      endSeconds: draftEnd,
    };
    setOverlays((previous) => [...previous, overlay]);
    setIsDialogOpen(false);
  };

  const deleteOverlay = (overlayId: string) => {
    setOverlays((previous) =>
      previous.filter((overlay) => overlay.id !== overlayId)
    );
  };

  const onDoneClick = () => {
    setUiNote("Interface only for now. Backend processing will be wired next.");
  };

  return (
    <>
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8">
        <section className="neon-panel rounded-3xl p-6 md:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <span className="neon-pill">Text overlay</span>
              <h1 className="mt-4 font-display text-3xl font-semibold sm:text-4xl">
                Create Text Overlay
              </h1>
              <p className="mt-2 text-muted">
                Design-only screen. Add and remove overlays before backend wiring.
              </p>
            </div>
            <Link className="neon-button neon-button-ghost" href="/videos">
              Back to videos
            </Link>
          </div>
        </section>

        <section className="neon-panel rounded-3xl p-5 md:p-7">
          <div className="grid gap-6 lg:grid-cols-[minmax(0,2.1fr)_minmax(280px,1fr)]">
            <div className="space-y-5">
              <div className="rounded-2xl border border-white/15 bg-black/25 p-4">
                <p className="text-sm font-semibold uppercase tracking-[0.25em] text-soft">
                  Video
                </p>
                <h2 className="mt-2 text-xl font-semibold">
                  {video?.video_title || "Selected video"}
                </h2>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="neon-chip">ID: {videoId}</span>
                  <span className="neon-chip">
                    Duration: {formatClock(videoDuration)}
                  </span>
                  {video?.status && (
                    <span className="neon-chip">Status: {video.status}</span>
                  )}
                </div>
                {video?.output_file_location && (
                  <p
                    className="mt-3 max-w-full truncate text-xs text-muted"
                    title={video.output_file_location}
                  >
                    File: {fileNameFromPath(video.output_file_location)}
                  </p>
                )}
              </div>

              <div className="rounded-2xl border border-white/15 bg-black/25 p-3">
                {isLoading ? (
                  <div className="flex aspect-video items-center justify-center rounded-xl border border-white/15 bg-black/35 text-sm text-soft">
                    Loading video...
                  </div>
                ) : error ? (
                  <div className="flex aspect-video items-center justify-center rounded-xl border border-rose-400/40 bg-rose-500/10 px-3 text-sm text-rose-200">
                    {error}
                  </div>
                ) : videoDownloadUrl ? (
                  <video
                    className="aspect-video w-full rounded-xl border border-white/10 bg-black/50"
                    controls
                    src={videoDownloadUrl}
                  />
                ) : (
                  <div className="flex aspect-video items-center justify-center rounded-xl border border-white/15 bg-black/35 px-3 text-center text-sm text-soft">
                    Video preview is available when the video status is completed.
                  </div>
                )}
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <button
                  className="neon-button neon-button-ghost w-full"
                  type="button"
                  onClick={openOverlayDialog}
                  disabled={!canAddOverlay}
                  title={
                    canAddOverlay
                      ? "Add a text overlay"
                      : "Video duration is required to define overlay times"
                  }
                >
                  Add Text Overlay
                </button>
                <button
                  className="neon-button neon-button-primary w-full"
                  type="button"
                  onClick={onDoneClick}
                >
                  Done (Process Video)
                </button>
              </div>

              {uiNote && (
                <p className="rounded-2xl border border-white/20 bg-black/25 px-4 py-3 text-sm text-muted">
                  {uiNote}
                </p>
              )}
            </div>

            <aside className="rounded-2xl border border-white/15 bg-black/20 p-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-lg font-semibold">Overlays</h3>
                <span className="neon-chip">{overlays.length} total</span>
              </div>
              <div className="mt-4 space-y-3">
                {overlays.length === 0 ? (
                  <p className="rounded-xl border border-white/15 bg-black/25 px-3 py-3 text-sm text-soft">
                    No overlays added yet.
                  </p>
                ) : (
                  overlays.map((overlay) => (
                    <article
                      key={overlay.id}
                      className="rounded-xl border border-white/20 bg-black/25 px-3 py-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold">
                            Text: {overlay.text}
                          </p>
                          <p className="mt-1 text-xs text-muted">
                            Start Time: {formatClock(overlay.startSeconds)}
                          </p>
                          <p className="text-xs text-muted">
                            End Time: {formatClock(overlay.endSeconds)}
                          </p>
                        </div>
                        <button
                          className="text-rose-200 underline decoration-rose-400/70 underline-offset-4 transition hover:text-rose-100"
                          type="button"
                          onClick={() => deleteOverlay(overlay.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </article>
                  ))
                )}
              </div>
            </aside>
          </div>
        </section>
      </div>

      {isDialogOpen && (
        <div
          className="fixed inset-0 z-30 flex items-center justify-center bg-black/60 px-4 py-8"
          role="dialog"
          aria-modal="true"
          aria-label="Add text overlay"
        >
          <div className="neon-panel w-full max-w-xl rounded-3xl p-6">
            <h2 className="font-display text-2xl font-semibold">Add Text Overlay</h2>
            <p className="mt-1 text-sm text-muted">
              Select text and timing in <span className="font-mono">mm:ss</span>.
            </p>

            <div className="mt-5 space-y-5">
              <label className="block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.25em] text-soft">
                  Text
                </span>
                <input
                  className="neon-input"
                  type="text"
                  value={draftText}
                  onChange={(event) => setDraftText(event.target.value)}
                  placeholder="Enter overlay text"
                  maxLength={120}
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.25em] text-soft">
                  Start Time: {formatClock(draftStart)}
                </span>
                <input
                  className="neon-range w-full"
                  type="range"
                  min={0}
                  max={maxStart}
                  step={1}
                  value={draftStart}
                  onChange={(event) => onStartChange(Number(event.target.value))}
                />
                <p className="mt-1 text-xs text-muted">
                  From {formatClock(0)} to {formatClock(maxStart)}
                </p>
              </label>

              <label className="block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.25em] text-soft">
                  End Time: {formatClock(draftEnd)}
                </span>
                <input
                  className="neon-range w-full"
                  type="range"
                  min={minEnd}
                  max={videoDuration}
                  step={1}
                  value={draftEnd}
                  onChange={(event) => onEndChange(Number(event.target.value))}
                />
                <p className="mt-1 text-xs text-muted">
                  Must be greater than start time ({formatClock(draftStart)})
                </p>
              </label>
            </div>

            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button
                className="neon-button neon-button-ghost"
                type="button"
                onClick={closeOverlayDialog}
              >
                Cancel
              </button>
              <button
                className="neon-button neon-button-primary"
                type="button"
                onClick={addOverlay}
                disabled={!canCreateDraft}
              >
                Add Overlay
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
