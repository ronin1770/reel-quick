"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type RawPost = {
  _id?: string;
  code?: string;
  name?: string;
  country?: string;
  dob?: string;
  excellence_field?: string;
  challenges_faced?: string;
  posted?: boolean;
};

type PersonBio = {
  _id?: string;
  code?: string;
  name?: string;
  country?: string;
  dob?: string;
  excellence_field?: string;
  challenges?: string;
};

type Quotes = {
  _id?: string;
  code?: string;
  quotes?: string;
  quote_image_paths?: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const PAGE_SIZE = 200;

const fallback = (value?: string) => value?.trim() || "-";

const getCode = (entry?: { code?: string }) => entry?.code?.trim() || null;

const parsePipeSeparated = (value?: string) =>
  (value ?? "")
    .split("|")
    .map((item) => item.trim())
    .filter(Boolean);

const parseQuotes = (value?: string) => {
  if (!value?.trim()) return [];
  const parts = value.includes("|")
    ? parsePipeSeparated(value)
    : value
        .split(/\n+/)
        .map((item) => item.trim())
        .filter(Boolean);
  return parts.map((item) => item.replace(/^\d+[\).\-\s]+/, "").trim());
};

const getErrorMessage = async (response: Response) => {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
  } catch {
    return null;
  }
  return null;
};

export default function PostsPage() {
  const [personalities, setPersonalities] = useState<RawPost[]>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [bio, setBio] = useState<PersonBio | null>(null);
  const [quotes, setQuotes] = useState<Quotes | null>(null);

  const [isLoadingPersonalities, setIsLoadingPersonalities] = useState(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [isMarkingPosted, setIsMarkingPosted] = useState(false);

  const [listError, setListError] = useState<string | null>(null);
  const [detailsError, setDetailsError] = useState<string | null>(null);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchPersonalities = useCallback(async () => {
    setIsLoadingPersonalities(true);
    setListError(null);

    try {
      const withQuotesUrl = new URL("/raw_posts", API_BASE);
      withQuotesUrl.searchParams.set("page", "1");
      withQuotesUrl.searchParams.set("page_size", String(PAGE_SIZE));
      withQuotesUrl.searchParams.set("quote_created", "true");

      let response = await fetch(withQuotesUrl.toString(), { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Unable to load personalities (${response.status})`);
      }

      let data = (await response.json()) as RawPost[];
      let records = Array.isArray(data) ? data : [];

      if (records.length === 0) {
        const fallbackUrl = new URL("/raw_posts", API_BASE);
        fallbackUrl.searchParams.set("page", "1");
        fallbackUrl.searchParams.set("page_size", String(PAGE_SIZE));
        response = await fetch(fallbackUrl.toString(), { cache: "no-store" });
        if (response.ok) {
          data = (await response.json()) as RawPost[];
          records = Array.isArray(data) ? data : [];
        }
      }

      setPersonalities(records);
      setSelectedCode((prev) => {
        if (prev && records.some((entry) => getCode(entry) === prev)) {
          return prev;
        }
        return getCode(records[0]);
      });
    } catch (error) {
      setListError(
        error instanceof Error ? error.message : "Unable to load personalities."
      );
      setPersonalities([]);
      setSelectedCode(null);
      setBio(null);
      setQuotes(null);
    } finally {
      setIsLoadingPersonalities(false);
    }
  }, []);

  const fetchPersonalityDetails = useCallback(async (code: string) => {
    setIsLoadingDetails(true);
    setDetailsError(null);
    setBio(null);
    setQuotes(null);

    try {
      const [bioResponse, quotesResponse] = await Promise.all([
        fetch(`${API_BASE}/person-bio/${encodeURIComponent(code)}`, {
          cache: "no-store",
        }),
        fetch(`${API_BASE}/quotes/${encodeURIComponent(code)}`, {
          cache: "no-store",
        }),
      ]);

      if (bioResponse.ok) {
        const bioData = (await bioResponse.json()) as PersonBio;
        setBio(bioData);
      }

      if (quotesResponse.ok) {
        const quotesData = (await quotesResponse.json()) as Quotes;
        setQuotes(quotesData);
      }

      if (!bioResponse.ok && !quotesResponse.ok) {
        throw new Error("No bio or quotes found for this personality.");
      }
    } catch (error) {
      setDetailsError(
        error instanceof Error
          ? error.message
          : "Unable to load personality details."
      );
    } finally {
      setIsLoadingDetails(false);
    }
  }, []);

  useEffect(() => {
    fetchPersonalities();
  }, [fetchPersonalities]);

  useEffect(() => {
    if (!selectedCode) {
      setBio(null);
      setQuotes(null);
      setDetailsError(null);
      return;
    }
    fetchPersonalityDetails(selectedCode);
  }, [fetchPersonalityDetails, selectedCode]);

  const selectedIndex = useMemo(
    () => personalities.findIndex((entry) => getCode(entry) === selectedCode),
    [personalities, selectedCode]
  );

  const selectedPersonality =
    selectedIndex >= 0 ? personalities[selectedIndex] : null;

  const name = fallback(bio?.name ?? selectedPersonality?.name);
  const country = fallback(bio?.country ?? selectedPersonality?.country);
  const dob = fallback(bio?.dob ?? selectedPersonality?.dob);
  const field = fallback(
    bio?.excellence_field ?? selectedPersonality?.excellence_field
  );
  const rawBioText = bio?.challenges ?? selectedPersonality?.challenges_faced;
  const bioText = useMemo(() => {
    const parts = parsePipeSeparated(rawBioText);
    if (parts.length > 1) {
      return parts.join("\n");
    }
    return fallback(rawBioText);
  }, [rawBioText]);

  const quotesList = useMemo(() => parseQuotes(quotes?.quotes), [quotes?.quotes]);
  const quoteImageCandidates = useMemo(
    () => parsePipeSeparated(quotes?.quote_image_paths),
    [quotes?.quote_image_paths]
  );

  const canGoPrevious = selectedIndex > 0;
  const canGoNext =
    selectedIndex !== -1 && selectedIndex < personalities.length - 1;

  const handleCopy = async () => {
    if (!selectedPersonality) return;
    const textToCopy = [
      `Name: ${name}`,
      `Date of Birth: ${dob}`,
      `Country: ${country}`,
      `Excellence Field: ${field}`,
      "",
      "BIO:",
      bioText,
    ].join("\n");

    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopyMessage("Copied to clipboard.");
    } catch {
      setCopyMessage("Unable to copy. Clipboard access was denied.");
    }
  };

  const handleMarkPosted = async () => {
    const selectedId = selectedPersonality?._id?.trim();
    if (!selectedId) return;
    setIsMarkingPosted(true);
    setActionMessage(null);

    try {
      const response = await fetch(
        `${API_BASE}/monthly-figures/${encodeURIComponent(selectedId)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            posted: true,
            posted_on: new Date().toISOString(),
          }),
        }
      );

      if (!response.ok) {
        const message = await getErrorMessage(response);
        throw new Error(message ?? `Unable to mark as posted (${response.status}).`);
      }

      const nextCode =
        getCode(personalities[selectedIndex + 1]) ??
        getCode(personalities[selectedIndex - 1]) ??
        null;

      setPersonalities((prev) =>
        prev.filter((entry) => entry._id !== selectedId)
      );
      setSelectedCode(nextCode);
      setActionMessage("Marked as posted and removed from list.");
    } catch (error) {
      setActionMessage(
        error instanceof Error ? error.message : "Unable to mark as posted."
      );
    } finally {
      setIsMarkingPosted(false);
    }
  };

  const onSelectPersonality = (code: string | null) => {
    if (!code) return;
    setSelectedCode(code);
    setCopyMessage(null);
    setActionMessage(null);
  };

  return (
    <div className="mx-auto w-full max-w-7xl">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="flex flex-col gap-6">
          <section className="neon-panel rounded-3xl p-6 md:p-8">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-soft">
                  Personality
                </p>
                <h1 className="mt-2 font-display text-3xl font-semibold sm:text-4xl">
                  {name}
                </h1>
                <p className="mt-2 text-sm text-muted">
                  Code:{" "}
                  <span className="font-mono">
                    {fallback(getCode(selectedPersonality ?? undefined) ?? undefined)}
                  </span>
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  className="neon-button neon-button-ghost"
                  type="button"
                  disabled={!canGoPrevious}
                  onClick={() => {
                    if (!canGoPrevious) return;
                    onSelectPersonality(getCode(personalities[selectedIndex - 1]));
                  }}
                >
                  Previous Personality
                </button>
                <button
                  className="neon-button neon-button-ghost"
                  type="button"
                  disabled={!canGoNext}
                  onClick={() => {
                    if (!canGoNext) return;
                    onSelectPersonality(getCode(personalities[selectedIndex + 1]));
                  }}
                >
                  Next Personality
                </button>
                <button
                  className="neon-button neon-button-primary"
                  type="button"
                  disabled={!selectedPersonality}
                  onClick={handleCopy}
                >
                  Copy
                </button>
              </div>
            </div>

            {copyMessage && <p className="mt-4 text-sm text-status-success">{copyMessage}</p>}
            {detailsError && (
              <p className="alert alert-error mt-4">
                {detailsError}
              </p>
            )}
          </section>

          <section className="neon-panel rounded-3xl p-6 md:p-8">
            <h2 className="font-display text-2xl font-semibold">Personality Bio</h2>
            <div className="mt-5 flex flex-wrap gap-2 text-xs">
              <span className="neon-chip">{country}</span>
              <span className="neon-chip">{dob}</span>
              <span className="neon-chip">{field}</span>
            </div>
            <p className="mt-5 min-h-[120px] whitespace-pre-line text-sm leading-relaxed text-muted">
              {isLoadingDetails ? "Loading bio..." : bioText}
            </p>
          </section>

          <section className="neon-panel rounded-3xl p-6 md:p-8">
            <h2 className="font-display text-2xl font-semibold">Quotes</h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {quotesList.length === 0 ? (
                <p className="text-sm text-soft">
                  {isLoadingDetails ? "Loading quotes..." : "No quotes found."}
                </p>
              ) : (
                quotesList.map((quote, index) => {
                  const imageSource = quoteImageCandidates[index];
                  const showImage =
                    imageSource?.startsWith("http://") ||
                    imageSource?.startsWith("https://");

                  return (
                    <article
                      key={`${quote}-${index}`}
                      className="neon-card flex min-h-[230px] flex-col rounded-2xl p-4"
                    >
                      {showImage ? (
                        <div
                          className="h-[110px] w-full rounded-xl bg-cover bg-center"
                          style={{ backgroundImage: `url(${imageSource})` }}
                        />
                      ) : (
                        <div className="placeholder-portrait relative h-[110px] w-full overflow-hidden rounded-xl">
                          <div className="placeholder-portrait__head absolute left-1/2 top-[20%] h-11 w-11 -translate-x-1/2 rounded-full" />
                          <div className="placeholder-portrait__body absolute bottom-0 left-1/2 h-14 w-24 -translate-x-1/2 rounded-t-[999px]" />
                        </div>
                      )}
                      <p className="mt-3 text-sm leading-relaxed text-muted">
                        {quote}
                      </p>
                      <span className="mt-auto pt-3 text-xs font-semibold uppercase tracking-[0.2em] text-soft">
                        #{fallback(
                          getCode(selectedPersonality ?? undefined) ?? undefined
                        )}
                      </span>
                    </article>
                  );
                })
              )}
            </div>
          </section>
        </div>

        <aside className="neon-panel flex h-fit flex-col rounded-3xl p-5 lg:sticky lg:top-28">
          <h2 className="font-display text-2xl font-semibold">
            List of Personalities
          </h2>
          <p className="mt-2 text-xs text-soft">
            {isLoadingPersonalities
              ? "Loading personalities..."
              : `${personalities.length} personalities`}
          </p>

          {listError && (
            <p className="alert alert-error mt-3">
              {listError}
            </p>
          )}

          <div className="mt-4 max-h-[460px] overflow-y-auto pr-1">
            <ul className="space-y-2">
              {personalities.map((entry, index) => {
                const code = getCode(entry);
                const isSelected = code === selectedCode;

                return (
                  <li key={entry._id ?? code ?? entry.name ?? `item-${index}`}>
                    <button
                      className={`selection-button w-full rounded-xl px-3 py-2 text-left text-sm underline underline-offset-4 transition ${
                        isSelected ? "selection-button-active" : ""
                      }`}
                      type="button"
                      onClick={() => onSelectPersonality(code)}
                      disabled={!code}
                    >
                      <span className="block font-semibold">
                        {fallback(entry.name)}
                      </span>
                      <span className="block text-xs text-soft">
                        {code ?? "Missing code"}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>

          <button
            className="neon-button neon-button-primary mt-6 w-full"
            type="button"
            disabled={
              !selectedPersonality?._id ||
              !!selectedPersonality.posted ||
              isMarkingPosted
            }
            onClick={handleMarkPosted}
          >
            {isMarkingPosted
              ? "Marking..."
              : selectedPersonality?.posted
                ? "Already Posted"
                : "Mark as posted"}
          </button>
          {actionMessage && (
            <p className="mt-3 text-sm text-status-success">{actionMessage}</p>
          )}
        </aside>
      </div>
    </div>
  );
}
