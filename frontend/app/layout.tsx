import type { Metadata } from "next";
import { Oxanium, Space_Grotesk } from "next/font/google";
import Image from "next/image";
import Link from "next/link";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const oxanium = Oxanium({
  variable: "--font-oxanium",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Reel Quick — Instagram Reel Creator",
  description:
    "Build neon-fast Instagram reels from your clips with a clean, creator-first workflow.",
  icons: {
    icon: "/logo-square.jpg",
    apple: "/logo-square.jpg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${spaceGrotesk.variable} ${oxanium.variable} antialiased`}
      >
        <div className="app-shell">
          <header className="app-header">
            <div className="app-header__inner">
              <Link
                aria-label="Reel Quick home"
                className="app-logo"
                href="/"
              >
                <Image
                  alt="Reel Quick"
                  height={60}
                  priority
                  src="/logo-rectangle.jpg"
                  width={220}
                />
              </Link>
              <nav className="app-nav">
                <Link className="app-nav__link" href="/">
                  Home
                </Link>
                <Link className="app-nav__link" href="/create_video">
                  Create
                </Link>
                <Link className="app-nav__link" href="/videos">
                  Videos
                </Link>
              </nav>
              <div className="app-header__actions">
                <Link
                  className="neon-button neon-button-primary"
                  href="/create_video"
                >
                  Create Video
                </Link>
              </div>
            </div>
          </header>
          <main className="app-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
