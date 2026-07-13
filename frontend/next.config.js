/** @type {import('next').NextConfig} */
// VisionLab's own FastAPI backend. Must point at THIS app's API, not a sibling's.
const API = process.env.VISIONLAB_API_URL || "http://127.0.0.1:8704";
module.exports = {
  reactStrictMode: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};
