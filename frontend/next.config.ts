import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Use backend URL from env var in production, localhost in dev
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
