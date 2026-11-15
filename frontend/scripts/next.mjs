import { spawn } from "node:child_process";
import { createRequire } from "node:module";

process.env.NEXT_TELEMETRY_DISABLED = "1";
const require = createRequire(import.meta.url);
const cli = require.resolve("next/dist/bin/next");
const child = spawn(process.execPath, [cli, ...process.argv.slice(2)], {
  stdio: "inherit",
  env: process.env,
});
child.on("error", (error) => { console.error("Could not start Next.js:", error.message); process.exitCode = 1; });
child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  else process.exitCode = code ?? 1;
});
