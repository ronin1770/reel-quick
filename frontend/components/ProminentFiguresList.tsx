"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type ProminentFigure = {
  _id?: string;
  id?: string;
  code?: string;
  name?: string;
  country?: string;
  dob?: string;
  excellence_field?: string;
  quote_created?: boolean;
  posted?: boolean;
  quote_created_on?: string | null;
  posted_on?: string | null;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const PAGE_SIZE = 20;

const buildRawPostsUrl = (quoteCreated: QuoteFilter, page: number) => {
  const url = new URL("/raw_posts", API_BASE);
  url.searchParams.set("page", String(page));
  url.searchParams.set("page_size", String(PAGE_SIZE));
  if (quoteCreated === "created") {
    url.searchParams.set("quote_created", "true");
  } else if (quoteCreated === "pending") {
    url.searchParams.set("quote_created", "false");
  }
  return url.toString();
};

const formatDate = (value?: string) => {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(date);
};

const fallback = (value?: string) => value?.trim() || "—";
const getFigureCode = (figure: ProminentFigure) =>
  figure.code?.trim() || null;

type QuoteFilter = "all" | "created" | "pending";

export default function ProminentFiguresList() {
  const [figures, setFigures] = useState<ProminentFigure[]>([]);
  const [page, setPage] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [quoteFilter, setQuoteFilter] = useState<QuoteFilter>("created");

  const fetchFigures = useCallback(async (pageToLoad: number) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(buildRawPostsUrl(quoteFilter, pageToLoad), {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`Unable to load prominent figures (${response.status})`);
      }
      const data = (await response.json()) as ProminentFigure[];
      const totalCountHeader = response.headers.get("x-total-count");
      const parsedTotal = totalCountHeader
        ? Number.parseInt(totalCountHeader, 10)
        : Number.NaN;
      setFigures(Array.isArray(data) ? data : []);
      setTotalRecords(Number.isFinite(parsedTotal) ? parsedTotal : data.length);
      setPage(pageToLoad);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load prominent figures."
      );
    } finally {
      setIsLoading(false);
    }
  }, [quoteFilter]);

  useEffect(() => {
    fetchFigures(1);
  }, [fetchFigures, quoteFilter]);

  const stats = useMemo(() => {
    const postedCount = figures.filter((item) => item.posted).length;
    const readyCount = figures.filter((item) => item.quote_created).length;
    return {
      total: totalRecords,
      posted: postedCount,
      ready: readyCount,
    };
  }, [figures, totalRecords]);

  const totalPages = Math.max(1, Math.ceil(totalRecords / PAGE_SIZE));
  const canGoPrev = page > 1;
  const canGoNext = page < totalPages;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-10">
      <section className="neon-panel rounded-3xl p-6 md:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-3">
            <span className="neon-pill">Prominent figures</span>
            <h1 className="font-display text-3xl font-semibold sm:text-4xl">
              Quotes & bios ready
            </h1>
            <p className="text-muted">
              Pulled from raw posts with quotes and bios already created.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <span className="neon-chip">{stats.total} total</span>
            <span className="neon-chip">{stats.ready} ready</span>
            <span className="neon-chip">{stats.posted} posted</span>
          </div>
        </div>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link
              className="neon-button neon-button-primary"
              href="/prominent_figures/monthly_figures"
            >
              New Monthly Figures
            </Link>
            <button
              className="neon-button neon-button-ghost"
              type="button"
              onClick={() => fetchFigures(page)}
              disabled={isLoading}
            >
              {isLoading ? "Refreshing..." : "Refresh"}
            </button>
            <label className="text-xs font-semibold uppercase tracking-[0.3em] text-soft">
              Quote status
            </label>
            <select
              className="neon-input w-[200px]"
              value={quoteFilter}
              onChange={(event) =>
                setQuoteFilter(event.target.value as QuoteFilter)
              }
            >
              <option value="created">Quotes created</option>
              <option value="pending">Quotes pending</option>
              <option value="all">All</option>
            </select>
          </div>
        {error && <div className="alert alert-error mt-4">{error}</div>}
      </section>

      <section className="neon-panel rounded-3xl p-5 md:p-7">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-soft">
              Posts list
            </p>
            <p className="text-xs text-muted">
              Showing name, country, date of birth, and field of excellence.
            </p>
          </div>
          <div className="text-xs text-muted">
            {quoteFilter === "created"
              ? "Showing figures with quotes created."
              : quoteFilter === "pending"
                ? "Showing figures waiting on quotes."
                : "Showing all figures."}
            {" "}
            ({figures.length} of {totalRecords})
          </div>
        </div>

        <div className="mt-6 overflow-x-auto">
          {figures.length === 0 ? (
            <p className="text-sm text-soft">
              {isLoading
                ? "Loading prominent figures..."
                : "No prominent figures found yet."}
            </p>
          ) : (
            <table className="min-w-full text-left text-sm">
              <thead className="table-head text-xs uppercase tracking-[0.3em]">
                <tr>
                  <th className="py-3 pr-6">Name</th>
                  <th className="py-3 pr-6">Country</th>
                  <th className="py-3 pr-6">Date of Birth</th>
                  <th className="py-3 pr-6">Field</th>
                  <th className="py-3">Details</th>
                </tr>
              </thead>
              <tbody>
                {figures.map((figure) => {
                  const code = getFigureCode(figure);
                  const key =
                    code ?? figure._id ?? figure.id ?? figure.name ?? "row";
                  return (
                    <tr key={key} className="table-row">
                      <td className="py-4 pr-6 align-top">
                        <p className="text-base font-semibold">
                          {fallback(figure.name)}
                        </p>
                      </td>
                      <td className="py-4 pr-6 align-top text-xs text-muted">
                        {fallback(figure.country)}
                      </td>
                      <td className="py-4 pr-6 align-top text-xs text-soft">
                        {formatDate(figure.dob)}
                      </td>
                      <td className="py-4 pr-6 align-top text-xs text-muted">
                        {fallback(figure.excellence_field)}
                      </td>
                      <td className="py-4 align-top text-xs">
                        {code ? (
                          <Link
                            className="theme-link"
                            href={`/prominent_figures/${encodeURIComponent(code)}`}
                          >
                            View details
                          </Link>
                        ) : (
                          <span className="text-soft">Missing code</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted">
            Page {page} of {totalPages}
          </p>
          <div className="flex items-center gap-3">
            <button
              className="neon-button neon-button-ghost"
              type="button"
              onClick={() => fetchFigures(page - 1)}
              disabled={!canGoPrev || isLoading}
            >
              Prev
            </button>
            <button
              className="neon-button neon-button-ghost"
              type="button"
              onClick={() => fetchFigures(page + 1)}
              disabled={!canGoNext || isLoading}
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
