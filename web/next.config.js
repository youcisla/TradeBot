/** @type {import('next').NextConfig} */
const nextConfig = {
  // ── Performance ────────────────────────────────────────────────────────────
  compress: true,

  // ── Cache headers for API routes ─────────────────────────────────────────
  async headers() {
    return [
      // No-cache for live data endpoints
      {
        source: "/api/status",
        headers: [
          { key: "Cache-Control", value: "no-store, must-revalidate, max-age=0" },
        ],
      },
      {
        source: "/api/trades",
        headers: [
          { key: "Cache-Control", value: "no-store, must-revalidate, max-age=0" },
        ],
      },
      {
        source: "/api/events",
        headers: [
          { key: "Cache-Control", value: "no-store, must-revalidate, max-age=0" },
        ],
      },
      {
        source: "/api/risk",
        headers: [
          { key: "Cache-Control", value: "no-store, must-revalidate, max-age=0" },
        ],
      },
      {
        source: "/api/intelligence",
        headers: [
          { key: "Cache-Control", value: "no-store, must-revalidate, max-age=0" },
        ],
      },
      // Short cache for analytics (aggregated, refreshes on interval)
      {
        source: "/api/analytics",
        headers: [
          { key: "Cache-Control", value: "public, max-age=10, stale-while-revalidate=30" },
        ],
      },
      // Longer cache for backtest status
      {
        source: "/api/backtest/status",
        headers: [
          { key: "Cache-Control", value: "public, max-age=2, stale-while-revalidate=8" },
        ],
      },
      // Static data — cache aggressively
      {
        source: "/api/candles",
        headers: [
          { key: "Cache-Control", value: "public, max-age=3600, stale-while-revalidate=86400" },
        ],
      },
      {
        source: "/api/ict",
        headers: [
          { key: "Cache-Control", value: "public, max-age=30, stale-while-revalidate=60" },
        ],
      },
      {
        source: "/api/learning",
        headers: [
          { key: "Cache-Control", value: "public, max-age=30, stale-while-revalidate=60" },
        ],
      },
      // Static Next.js assets — immutable, long cache
      {
        source: "/_next/static/:path*",
        headers: [
          { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
        ],
      },
      // Google Fonts — allow caching
      {
        source: "/fonts/:path*",
        headers: [
          { key: "Cache-Control", value: "public, max-age=2592000, immutable" },
        ],
      },
    ];
  },

  poweredByHeader: false,
};

module.exports = nextConfig;
