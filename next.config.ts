import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  distDir: "out",
  trailingSlash: true,
  basePath: "/Hexamind",
  assetPrefix: "/Hexamind",
  images: {
    unoptimized: true
  }
};

export default nextConfig;
