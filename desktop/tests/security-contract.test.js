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
  assert.match(preload, /const\s*\{\s*contextBridge\s*,\s*ipcRenderer\s*\}\s*=\s*require\("electron"\)/);
  assert.match(preload, /contextBridge\.exposeInMainWorld\("cog"/);
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


test("provider credentials stay behind OS-backed encryption in the main process", async () => {
  const main = await read("main/main.js");
  const preload = await read("preload/preload.js");
  const renderer = await read("renderer/renderer.js");
  assert.match(main, /safeStorage\.isEncryptionAvailable\(\)/);
  assert.match(main, /safeStorage\.encryptString/);
  assert.match(main, /safeStorage\.decryptString/);
  assert.match(main, /getSelectedStorageBackend/);
  assert.match(preload, /getSecureStorageStatus/);
  assert.match(renderer, /secure-storage-status/);
  assert.match(main, /X-Provider-API-Key/);
  assert.match(preload, /setProviderApiKey/);
  assert.doesNotMatch(renderer, /safeStorage|node:fs|electron/);
  assert.doesNotMatch(main, /localStorage|app\.db.*api.?key/i);
});

test("renderer exposes context, memory, claims, and settings views without HTML injection", async () => {
  const html = await read("renderer/index.html");
  const renderer = await read("renderer/renderer.js");
  for (const view of ["context", "memory", "claims", "settings"]) {
    assert.match(html, new RegExp(`data-view="${view}"`));
  }
  assert.match(renderer, /excluded_sources/);
  assert.match(renderer, /\/v1\/runs\//);
  assert.match(renderer, /\/v1\/memory/);
  assert.match(renderer, /\/v1\/claims/);
  assert.match(renderer, /\/v1\/settings/);
  assert.doesNotMatch(renderer, /\.innerHTML\b/);
});

test("context and memory panels reject stale requests and context follows the selected branch", async () => {
  const renderer = await read("renderer/renderer.js");
  const backendRuns = await read("../backend/src/cogplat/repos/runs.py");
  assert.match(renderer, /contextRequestSequence/);
  assert.match(renderer, /memoryRequestSequence/);
  assert.match(renderer, /conversationsRequestSequence/);
  assert.match(renderer, /runs\/latest/);
  assert.match(renderer, /requestSequence !== state\.memoryRequestSequence/);
  assert.match(renderer, /requestSequence !== state\.contextRequestSequence/);
  assert.match(backendRuns, /get_latest_chat_run_for_branch/);
});

test("renderer uses an in-app dialog instead of unsupported window.prompt", async () => {
  const html = await read("renderer/index.html");
  const renderer = await read("renderer/renderer.js");
  assert.match(html, /<dialog id="input-dialog"/);
  assert.match(html, /id="input-dialog-value"/);
  assert.match(renderer, /async function requestText\(/);
  assert.match(renderer, /dialog\.showModal\(\)/);
  assert.match(renderer, /await requestText\("Conversation name"\)/);
  assert.doesNotMatch(renderer, /window\.prompt\s*\(/);
});

test("desktop viewport stays fixed while chat and conversation list scroll independently", async () => {
  const css = await read("renderer/styles.css");
  assert.match(css, /html,\s*body\s*\{[^}]*height:\s*100%[^}]*overflow:\s*hidden/s);
  assert.match(css, /body\s*\{[^}]*height:\s*100vh/s);
  assert.match(css, /\.app-shell\s*\{[^}]*height:\s*100vh[^}]*overflow:\s*hidden/s);
  assert.match(css, /\.workspace\s*\{[^}]*height:\s*100vh[^}]*overflow:\s*hidden/s);
  assert.match(css, /\.chat-panel\s*\{[^}]*min-height:\s*0[^}]*overflow:\s*hidden/s);
  assert.match(css, /\.message-list\s*\{[^}]*overflow-y:\s*auto/s);
  assert.match(css, /\.composer\s*\{[^}]*flex:\s*0\s+0\s+auto/s);
  assert.match(css, /\.conversation-list\s*\{[^}]*overflow-y:\s*auto/s);
});
