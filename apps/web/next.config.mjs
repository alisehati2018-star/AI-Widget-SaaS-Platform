import createNextIntlPlugin from "next-intl/plugin";

/** @type {import('next').NextConfig} */

// Same-origin proxy to the FastAPI backend so the browser never hits CORS:
// the app calls /api/... and Next forwards to the backend origin.
const API_ORIGIN = process.env.API_ORIGIN || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/:path*` }];
  },
};

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

export default withNextIntl(nextConfig);
