const path = require("path");
require("dotenv").config({ path: path.resolve(__dirname, "../.env") });

/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    CRUCIX_URL: process.env.CRUCIX_URL || "http://localhost:3117",
  },
};
module.exports = nextConfig;
