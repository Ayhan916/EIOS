import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enables minimal self-contained output for Docker deployment
  output: "standalone",

  // Proxy /api/* requests to the backend during development
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
