import { defineConfig } from "@playwright/test";

const python = process.env.NINAI_TEST_PYTHON || "../engine/.venv/bin/python";
const quotedPython = "'" + python.replace(/'/g, "'\\''") + "'";

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  retries: 0,
  timeout: 30_000,
  globalTimeout: 180_000,
  use: { browserName: "chromium", viewport: { width: 1280, height: 900 }, trace: "retain-on-failure", screenshot: "only-on-failure" },
  webServer: [
    {
      command: `${quotedPython} ../scripts/preview_desktop_acceptance.py --port 58045`,
      url: "http://127.0.0.1:58045/",
      reuseExistingServer: false,
      gracefulShutdown: { signal: "SIGINT", timeout: 5_000 },
    },
    {
      command: "python3 -m http.server 3034 --bind 127.0.0.1 --directory out",
      url: "http://127.0.0.1:3034/",
      reuseExistingServer: false,
    },
  ],
});
