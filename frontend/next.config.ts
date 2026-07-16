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
    config.resolve.alias.canvas = false;
    // pdfjs-dist v5 declares var __webpack_exports__ inside pdf.mjs which hoists
    // in strict-mode eval and makes webpack's preamble receive undefined.
    // The loader renames those 5 lines and replaces import.meta.url.
    config.module.rules.unshift({
      test: /node_modules\/pdfjs-dist\/build\/pdf\.mjs$/,
      use: [{ loader: require.resolve("./pdfjs-patch-loader.cjs") }],
    });
    return config;
  },
};

export default nextConfig;
