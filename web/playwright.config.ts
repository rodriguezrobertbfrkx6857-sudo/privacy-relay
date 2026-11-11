import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:8215",
    viewport: { width: 1440, height: 1000 },
  },
  webServer: {
    command: "uv run uvicorn app.main:app --host 127.0.0.1 --port 8215",
    cwd: "..",
    url: "http://127.0.0.1:8215/api/health",
    reuseExistingServer: false,
    env: { APP_DB: "data/e2e.sqlite3" },
  },
});
