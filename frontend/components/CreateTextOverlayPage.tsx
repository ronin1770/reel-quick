"use client";

import Link from "next/link";

type CreateTextOverlayPageProps = {
  videoId: string;
};

export default function CreateTextOverlayPage({
  videoId,
}: CreateTextOverlayPageProps) {
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <section className="neon-panel rounded-3xl p-6 md:p-8">
        <span className="neon-pill">Text overlay</span>
        <h1 className="mt-4 font-display text-3xl font-semibold sm:text-4xl">
          Create Text Overlay
        </h1>
        <p className="mt-3 text-muted">
          Overlay creator UI will be implemented next. This page is ready to use
          with the selected video.
        </p>
        <div className="mt-6 rounded-2xl border border-white/15 bg-black/20 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.25em] text-soft">Video ID</p>
          <p className="mt-1 font-mono text-sm text-cyan-200">{videoId}</p>
        </div>
        <div className="mt-6">
          <Link className="neon-button neon-button-ghost" href="/videos">
            Back to videos
          </Link>
        </div>
      </section>
    </div>
  );
}
