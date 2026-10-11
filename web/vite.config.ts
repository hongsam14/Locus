/// <reference types="vitest" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/setupTests.ts"],
    globalSetup: ["./src/test/globalSetup.ts"],
    // screen tests render whole pages; under a loaded run (CI, parallel files) some pass 5 s
    // and failed as time-outs that hid real results (V8 code review 01 #15)
    testTimeout: 15_000,
  },
});
