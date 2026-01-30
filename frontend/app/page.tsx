import Image from "next/image";
import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-16">
      <section className="grid items-center gap-12 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-8">
          <span className="neon-pill">Creator suite</span>
          <div className="space-y-4">
            <h1 className="font-display text-4xl font-semibold leading-tight sm:text-5xl lg:text-6xl">
              Reel Quick
            </h1>
            <p className="text-lg text-muted sm:text-xl">
              Build neon-fast Instagram reels from your clips. Trim, stack, and
              ship in a flow that feels like a studio.
            </p>
          </div>
          <div className="flex flex-wrap gap-4">
            <Link className="neon-button neon-button-primary" href="/create_video">
              Create Video
            </Link>
            <Link className="neon-button neon-button-ghost" href="/videos">
              View Videos
            </Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="neon-card rounded-2xl p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-soft">
                Clip Stack
              </p>
              <p className="mt-3 text-lg font-semibold">Organize fast</p>
              <p className="mt-2 text-sm text-muted">
                Queue up every take and keep the flow tight.
              </p>
            </div>
            <div className="neon-card rounded-2xl p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-soft">
                Trim Zone
              </p>
              <p className="mt-3 text-lg font-semibold">Precision cuts</p>
              <p className="mt-2 text-sm text-muted">
                Dial the perfect start and end on every clip.
              </p>
            </div>
            <div className="neon-card rounded-2xl p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-soft">
                Launch
              </p>
              <p className="mt-3 text-lg font-semibold">Ready to publish</p>
              <p className="mt-2 text-sm text-muted">
                Export a clean timeline built for reels.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="neon-panel rounded-3xl p-6">
            <div className="flex items-center gap-4">
              <div className="relative h-20 w-20 overflow-hidden rounded-2xl border border-white/10 shadow-[0_0_25px_rgba(255,45,199,0.4)]">
                <Image
                  alt="Reel Quick logo"
                  fill
                  sizes="80px"
                  src="/logo-square.jpg"
                  style={{ objectFit: "cover" }}
                />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-soft">
                  Studio
                </p>
                <p className="font-display text-2xl font-semibold">
                  Neon timeline control
                </p>
              </div>
            </div>
            <div className="mt-6 grid gap-3">
              <div className="neon-badge">Realtime preview</div>
              <div className="neon-badge">Clip-by-clip trimming</div>
              <div className="neon-badge">Stacked reel parts</div>
            </div>
          </div>
          <div className="neon-card rounded-3xl p-6">
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-soft">
              How it flows
            </p>
            <ol className="mt-4 space-y-3 text-sm text-muted">
              <li>1. Add your clips and select a hero video.</li>
              <li>2. Trim start/end points with the timeline sliders.</li>
              <li>3. Stack parts, then publish your reel.</li>
            </ol>
          </div>
        </div>
      </section>
    </div>
  );
}
