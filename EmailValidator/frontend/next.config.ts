import type { NextConfig } from "next";

// Bundled into the EzyMailer desktop app: the Python backend serves this
// build as static files (no Node.js runtime shipped with the app), so it
// has to be a static export rather than a server-rendered Next app.
const nextConfig: NextConfig = {
  output: "export",
};

export default nextConfig;
