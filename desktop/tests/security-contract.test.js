import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const desktopDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => readFile(path.join(desktopDir, relativePath), "utf8");

test("Electron window keeps renderer isolation and navigation restrictions enabled", async () => {
  const main = await read("main/main.js");
  assert.match(main, /contextIsolation:\s*true/);
  assert.match(main, /sandbox:\s*true/);
  assert.match(main, /nodeIntegration:\s*false/);
  assert.match(main, /webSecurity:\s*true/);
  assert.match(main, /setWindowOpenHandler\(\(\)\s*=>\s*\(\{\s*action:\s*"deny"\s*\}\)\)/);
  assert.match(main, /will-navigate[\s\S]*?preventDefault/);
  assert.match(main, /event\.senderFrame\s*!==\s*event\.sender\.mainFrame/);
});

test("renderer has no direct Node access and renders message text without HTML injection", async () => {
  const preload = await read("preload/preload.js");
  const renderer = await read("renderer/renderer.js");
  assert.match(preload, /contextBridge\.exposeInMainWorld\("cog"/);
  assert.doesNotMatch(preload, /\brequire\s*\(/);
  assert.doesNotMatch(renderer, /\brequire\s*\(|\bprocess\b/);
  assert.doesNotMatch(renderer, /\.innerHTML\b/);
  assert.match(renderer, /\.textContent\s*=/);
  assert.match(renderer, /allow_remote:\s*allowRemote/);
  assert.match(renderer, /elements\.allowRemote\.checked\s*=\s*false/);
});

test("main process injects the bearer token and rejects non-API paths", async () => {
  const main = await read("main/main.js");
  assert.match(main, /Authorization:\s*\`Bearer \$\{connection\.token\}\`/);
  assert.match(main, /requestPath\.startsWith\("\/v1\/"\)/);
  assert.match(main, /url\.origin !== connection\.baseUrl/);
});
