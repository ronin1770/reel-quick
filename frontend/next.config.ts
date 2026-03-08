import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/voice_cloner",
        destination: "/voice-cloner",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
