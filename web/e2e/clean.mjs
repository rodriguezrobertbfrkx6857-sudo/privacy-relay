import { unlinkSync, existsSync } from "node:fs";
for (const p of [
  "../data/e2e.sqlite3",
  "../data/e2e.sqlite3-wal",
  "../data/e2e.sqlite3-shm",
])
  if (existsSync(p)) unlinkSync(p);
