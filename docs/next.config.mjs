import { createMDX } from "fumadocs-mdx/next";

const withMDX = createMDX();

/** @type {import('next').NextConfig} */
const config = {
  basePath: "/cerbia",
  output: "export",
  distDir: "dist",
  reactStrictMode: true,
  trailingSlash: true,
  images: {
    unoptimized: true,
  }
};

export default withMDX(config);
