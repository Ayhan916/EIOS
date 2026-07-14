import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/:path*`,
      },
    ];
  },
  webpack: (config) => {
    // PDF.js requires canvas to be aliased to false in Next.js
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default nextConfig;
