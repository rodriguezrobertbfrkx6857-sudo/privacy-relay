# Verification record

Measured on 2026-11-11, Windows, Python 3.12.13, Node 22.20.0.

| Check | Observed result |
| --- | --- |
| pytest | 22 passed, 0 failed |
| Python statement coverage | 95.4% |
| Ruff | passed |
| TypeScript + Vite production build | passed |
| Playwright Chromium | 2 tests passed; primary workflow + audit + mobile layout |
| Viewports | 1440×1000 desktop and 390×844 mobile, including result state |
| Real local model | Not executed; no Ollama model was installed |
| Docker | Local daemon unavailable; image build and health check are in GitHub CI |

Evidence: [JUnit](test-results.xml), [machine-readable record](validation.json), [actual UI screenshot](screenshot.png). Source dependencies are frozen by uv.lock and package-lock.json.

A Starlette warning notes future migration from httpx to httpx2 for TestClient; tests pass with the locked dependency set. This is a research prototype, not a production security certification.

## What the tests establish

Tests exercise real domain logic and API behavior, including negative cases. Browser tests execute built frontend assets against a real FastAPI server. They do not measure broad model safety, unseen attack generalization or production capacity.

A fresh-database concurrent audit test covers the SQLite WAL initialization race found during live HTTP integration. After fixing initialization, the paired Sentinel service experiment completed all 36 cases without target errors.

CI uses the preinstalled Chrome channel on Ubuntu 24.04; local checks use Playwright Chromium. The same workflow and mobile assertions run in both. Browser provisioning is checked with `google-chrome --version`, and each CI job has a 15-minute timeout.
