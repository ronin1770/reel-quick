"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type VideoRecord = {
  video_id: string;
  video_title: string;
  video_size?: number | string | null;
  video_introduction?: string | null;
  creation_time?: string;
  modification_time?: string;
  active?: boolean;
  video_tags?: string[];
  status?: string;
  output_file_location?: string | null;
  job_id?: string | null;
  error_reason?: string | null;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const formatDateTime = (value?: string) => {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};

const normalizeStatus = (status?: string) =>
  (status ?? "created").toLowerCase();

const statusLabel = (status?: string) => {
  const normalized = normalizeStatus(status);
  if (normalized === "queued") return "Queued";
  if (normalized === "processing") return "Processing";
  if (normalized === "completed") return "Completed";
  if (normalized === "failed") return "Failed";
  if (normalized === "created") return "Created";
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
};

const statusClass = (status?: string) => {
  const normalized = normalizeStatus(status);
  if (normalized === "completed") return "text-emerald-200";
  if (normalized === "failed") return "text-rose-200";
  if (normalized === "processing") return "text-sky-200";
  if (normalized === "queued") return "text-indigo-200";
  if (normalized === "created") return "text-amber-200";
  return "text-soft";
};

const StatusPill = ({ status }: { status?: string }) => (
  <span
    className={`neon-badge text-[10px] font-semibold uppercase tracking-[0.25em] ${statusClass(
      status
    )}`}
  >
    {statusLabel(status)}
  </span>
);

const sortByRecent = (items: VideoRecord[]) =>
  [...items].sort((a, b) => {
    const aTime = new Date(a.modification_time ?? a.creation_time ?? 0).getTime();
    const bTime = new Date(b.modification_time ?? b.creation_time ?? 0).getTime();
    return bTime - aTime;
  });

export default function VideoList() {
  const [videos, setVideos] = useState<VideoRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<Record<string, boolean>>({});

  const fetchVideos = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/videos`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Unable to load videos (${response.status})`);
      }
      const data = (await response.json()) as VideoRecord[];
      setVideos(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load videos.");
    } finally {
      setIsLoading(false);
    }
  }, [API_BASE]);

  useEffect(() => {
    fetchVideos();
  }, [fetchVideos]);

  const handleDelete = useCallback(
    async (videoId: string) => {
      const confirmed = window.confirm(
        "Delete this video? This removes the video record and associated files."
      );
      if (!confirmed) return;

      setDeleting((prev) => ({ ...prev, [videoId]: true }));
      setError(null);

      try {
        const response = await fetch(`${API_BASE}/videos/${videoId}`, {
          method: "DELETE",
        });
        if (!response.ok) {
          throw new Error(`Unable to delete video (${response.status})`);
        }
        setVideos((prev) => prev.filter((video) => video.video_id !== videoId));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to delete video.");
      } finally {
        setDeleting((prev) => {
          const next = { ...prev };
          delete next[videoId];
          return next;
        });
      }
    },
    [API_BASE]
  );

  const grouped = useMemo(() => {
    const created: VideoRecord[] = [];
    const failed: VideoRecord[] = [];
    const attempted: VideoRecord[] = [];

    sortByRecent(videos).forEach((video) => {
      const normalized = normalizeStatus(video.status);
      if (normalized === "failed") {
        failed.push(video);
      } else if (normalized === "created") {
        created.push(video);
      } else {
        attempted.push(video);
      }
    });

    return { created, failed, attempted };
  }, [videos]);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-10">
      <section className="neon-panel rounded-3xl p-6 md:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-3">
            <span className="neon-pill">Video vault</span>
            <h1 className="font-display text-3xl font-semibold sm:text-4xl">
              Recent reels
            </h1>
            <p className="text-muted">
              Monitor everything you created, failed runs, and all attempted
              renders in one place.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <span className="neon-chip">{videos.length} total</span>
            <span className="neon-chip">{grouped.created.length} created</span>
            <span className="neon-chip">{grouped.attempted.length} attempted</span>
            <span className="neon-chip">{grouped.failed.length} failed</span>
          </div>
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            className="neon-button neon-button-ghost"
            type="button"
            onClick={fetchVideos}
            disabled={isLoading}
          >
            {isLoading ? "Refreshing..." : "Refresh"}
          </button>
          <Link className="neon-button neon-button-primary" href="/create_video">
            Create Video
          </Link>
        </div>
        {error && (
          <div className="mt-4 rounded-2xl border border-rose-400/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}
      </section>

      <section className="neon-panel rounded-3xl p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-soft">
              All videos
            </p>
            <p className="text-xs text-muted">
              Sorted by the most recent update.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-muted">
            <span className="neon-chip">{grouped.created.length} created</span>
            <span className="neon-chip">
              {grouped.attempted.length} attempted
            </span>
            <span className="neon-chip">{grouped.failed.length} failed</span>
          </div>
        </div>

        <div className="mt-5 overflow-x-auto">
          {videos.length === 0 ? (
            <p className="text-sm text-soft">
              {isLoading ? "Loading videos..." : "No created videos yet."}
            </p>
          ) : (
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-white/10 text-xs uppercase tracking-[0.3em] text-soft">
                <tr>
                  <th className="py-3 pr-6">Title</th>
                  <th className="py-3 pr-6">Status</th>
                  <th className="py-3 pr-6">Video ID</th>
                  <th className="py-3 pr-6">Size</th>
                  <th className="py-3 pr-6">Updated</th>
                  <th className="py-3 pr-6">Output / Error</th>
                  <th className="py-3">Delete</th>
                </tr>
              </thead>
              <tbody>
                {sortByRecent(videos).map((video) => (
                  <tr
                    key={video.video_id}
                    className="border-b border-white/10 last:border-b-0"
                  >
                    <td className="py-4 pr-6 align-top">
                      <p className="text-base font-semibold">
                        {video.video_title || "Untitled video"}
                      </p>
                      {video.video_introduction && (
                        <p className="mt-1 max-w-[260px] text-xs text-muted">
                          {video.video_introduction}
                        </p>
                      )}
                    </td>
                    <td className="py-4 pr-6 align-top">
                      <StatusPill status={video.status} />
                    </td>
                    <td className="py-4 pr-6 align-top text-xs text-soft">
                      <span className="font-mono">{video.video_id}</span>
                    </td>
                    <td className="py-4 pr-6 align-top text-xs text-muted">
                      {video.video_size ? String(video.video_size) : "—"}
                    </td>
                    <td className="py-4 pr-6 align-top text-xs text-soft">
                      {formatDateTime(
                        video.modification_time ?? video.creation_time
                      )}
                    </td>
                    <td className="py-4 align-top text-xs text-muted">
                      {video.error_reason ? (
                        <span className="text-rose-200">
                          Error: {video.error_reason}
                        </span>
                      ) : video.output_file_location ? (
                        <span
                          className="inline-block max-w-[220px] truncate"
                          title={video.output_file_location}
                        >
                          {video.output_file_location}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="py-4 align-top text-xs">
                      <button
                        className="text-rose-200 underline decoration-rose-400/70 underline-offset-4 transition hover:text-rose-100 disabled:cursor-not-allowed disabled:text-rose-200/60"
                        type="button"
                        onClick={() => handleDelete(video.video_id)}
                        disabled={Boolean(deleting[video.video_id])}
                      >
                        {deleting[video.video_id] ? "Deleting..." : "Delete"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
