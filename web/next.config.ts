import type { NextConfig } from "next";

const internalApi =
  process.env.INTERNAL_API_URL ||
  (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "http://inspear-api:8000");

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${internalApi}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;