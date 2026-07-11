"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";

type RawPostDetail = {
  _id: string;
  code?: string;
  name?: string;
  country?: string;
  dob?: string;
  excellence_field?: string;
  challenges_faced?: string;
  quote_created?: boolean;
  posted?: boolean;
  added_on?: string;
  updated_on?: string;
  quote_created_on?: string | null;
  posted_on?: string | null;
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

const fallback = (value?: string) => value?.trim() || "—";

export default function RawPostDetailPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = use(params);
  const [rawPost, setRawPost] = useState<RawPostDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRawPost = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE}/raw_posts/${encodeURIComponent(code)}`,
        {
          cache: "no-store",
        }
      );
      if (!response.ok) {
        throw new Error(`Unable to load raw post (${response.status})`);
      }
      const data = (await response.json()) as RawPostDetail;
      setRawPost(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load raw post.");
      setRawPost(null);
    } finally {
      setIsLoading(false);
    }
  }, [code]);

  useEffect(() => {
    fetchRawPost();
  }, [fetchRawPost]);

  if (!rawPost && !isLoading) {
    return (
      <div className="mx-auto w-full max-w-4xl">
        <section className="neon-panel rounded-3xl p-6 md:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-soft">
            Raw post
          </p>
          <h1 className="mt-3 font-display text-3xl font-semibold">
            Raw post not found
          </h1>
          <p className="mt-2 text-sm text-muted">
            {error ?? "The selected raw post could not be loaded."}
          </p>
          <Link
            className="theme-link mt-6 inline-flex text-sm font-semibold"
            href="/prominent_figures"
          >
            Back to posts
          </Link>
        </section>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-8">
      <section className="neon-panel rounded-3xl p-6 md:p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-soft">
              Raw post detail
            </p>
            <h1 className="mt-2 font-display text-3xl font-semibold">
              {rawPost ? fallback(rawPost.name) : "Loading..."}
            </h1>
            <p className="mt-2 text-sm text-muted">
              Code:{" "}
              <span className="font-mono">
                {rawPost ? fallback(rawPost.code ?? code) : code}
              </span>
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="neon-badge">
              {rawPost?.quote_created ? "Quotes created" : "Quotes pending"}
            </span>
            <span className="neon-badge">
              {rawPost?.posted ? "Posted" : "Not posted"}
            </span>
          </div>
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            className="neon-button neon-button-ghost"
            href="/prominent_figures"
          >
            Back to posts
          </Link>
          <button
            className="neon-button neon-button-ghost"
            type="button"
            onClick={fetchRawPost}
            disabled={isLoading}
          >
            {isLoading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        {isLoading && (
          <p className="mt-4 text-sm text-soft">Loading raw post details...</p>
        )}
      </section>

      {rawPost && (
        <>
          <section className="neon-panel rounded-3xl p-6 md:p-8">
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-soft">
              Bio snapshot
            </p>
            <div className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
              <div className="neon-card rounded-2xl p-4">
                <p className="text-xs uppercase tracking-[0.25em] text-soft">
                  Country
                </p>
                <p className="mt-2 text-base font-semibold">
                  {fallback(rawPost.country)}
                </p>
              </div>
              <div className="neon-card rounded-2xl p-4">
                <p className="text-xs uppercase tracking-[0.25em] text-soft">
                  Date of birth
                </p>
                <p className="mt-2 text-base font-semibold">
                  {formatDateTime(rawPost.dob)}
                </p>
              </div>
              <div className="neon-card rounded-2xl p-4 sm:col-span-2">
                <p className="text-xs uppercase tracking-[0.25em] text-soft">
                  Field of excellence
                </p>
                <p className="mt-2 text-base font-semibold">
                  {fallback(rawPost.excellence_field)}
                </p>
              </div>
              <div className="neon-card rounded-2xl p-4 sm:col-span-2">
                <p className="text-xs uppercase tracking-[0.25em] text-soft">
                  Challenges faced
                </p>
                <p className="mt-2 text-sm text-muted">
                  {fallback(rawPost.challenges_faced)}
                </p>
              </div>
            </div>
          </section>

          <section className="neon-panel rounded-3xl p-6 md:p-8">
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-soft">
              Timeline
            </p>
            <div className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
              <div className="neon-card rounded-2xl p-4">
                <p className="text-xs uppercase tracking-[0.25em] text-soft">
                  Added on
                </p>
                <p className="mt-2 text-base font-semibold">
                  {formatDateTime(rawPost.added_on)}
                </p>
              </div>
              <div className="neon-card rounded-2xl p-4">
                <p className="text-xs uppercase tracking-[0.25em] text-soft">
                  Updated on
                </p>
                <p className="mt-2 text-base font-semibold">
                  {formatDateTime(rawPost.updated_on)}
                </p>
              </div>
              <div className="neon-card rounded-2xl p-4">
                <p className="text-xs uppercase tracking-[0.25em] text-soft">
                  Quote created on
                </p>
                <p className="mt-2 text-base font-semibold">
                  {formatDateTime(rawPost.quote_created_on ?? undefined)}
                </p>
              </div>
              <div className="neon-card rounded-2xl p-4">
                <p className="text-xs uppercase tracking-[0.25em] text-soft">
                  Posted on
                </p>
                <p className="mt-2 text-base font-semibold">
                  {formatDateTime(rawPost.posted_on ?? undefined)}
                </p>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
