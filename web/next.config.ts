import type { NextConfig } from "next";

const upstreamApiUrl = (
  process.env.NEXT_PUBLIC_IZFIN_API_URL ??
  "https://izfin-api-469145462773.europe-west1.run.app"
).replace(/\/$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/izfin-api/:path*",
        destination: `${upstreamApiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
