import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  output: "export",
  distDir: "out",
  trailingSlash: true,
  basePath: isProd ? "/Hexamind" : "",
  assetPrefix: isProd ? "/Hexamind" : "",
  images: {
    unoptimized: true
  }
};

export default nextConfig;
