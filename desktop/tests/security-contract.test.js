import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { runInNewContext } from "node:vm";

import { validateExplorerRequest } from "../main/explorer-tools.js";
import { readChatImage } from "../renderer/chat-images.js";
import { readSelectedTextFile } from "../renderer/chat-tools.js";

const desktopDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => readFile(path.join(desktopDir, relativePath), "utf8");
const pngData = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRcsAAAAASUVORK5CYII=";

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
});

test("chat defaults to local and authorizes remote turns only after provider selection", async () => {
  const html = await read("renderer/index.html");
  const renderer = await read("renderer/renderer.js");
  assert.doesNotMatch(html, /id="allow-remote"/);

  const remote = { id: "openrouter_free", label: "OpenRouter Free", is_remote: true };
  const local = { id: "ollama", label: "Ollama", is_remote: false };
  const requests = [];
  const options = [];
  let images = [];
  const state = { selectedProviderId: null, selectedBranchId: "branch" };
  const elements = {
    providerSelect: {
      replaceChildren: () => { options.length = 0; },
      append: (option) => options.push(option),
    },
    messageInput: { value: "hello" },
    chatStatus: {},
    sendButton: {},
  };
  let providers = [remote];
  const context = {
    state, elements,
    api: async () => ({ items: providers }),
    makeOption: (value, label) => ({ value, label }),
    selectProvider: async (id) => { state.selectedProviderId = id; },
    selectedModel: () => "test-model",
    chatImages: { payload: () => images, reset: () => { images = []; } },
    appendMessage: () => ({}),
    scrollChatToBottom: () => {},
    window: { cog: { stream: (_path, request) => requests.push(request) } },
  };
  const providerCode = renderer.slice(renderer.indexOf("async function loadProviders()"), renderer.indexOf("const ollamaControls"));
  const sendCode = renderer.slice(renderer.indexOf("async function sendMessage("), renderer.indexOf("const views ="));
  runInNewContext(providerCode + sendCode, context);

  await context.loadProviders();
  assert.equal(state.selectedProviderId, null);
  assert.equal(elements.providerSelect.value, "");
  assert.equal(options[1].label, "OpenRouter Free (remote)");
  await context.sendMessage({ preventDefault() {} });
  assert.equal(requests.length, 0);

  providers = [remote, local];
  await context.loadProviders();
  assert.equal(state.selectedProviderId, "ollama");
  await context.sendMessage({ preventDefault() {} });
  assert.equal(requests[0].body.allow_remote, false);
  assert.equal("images" in requests[0].body, false);

  await context.selectProvider(remote.id);
  elements.sendButton.disabled = false;
  elements.messageInput.value = "hello again";
  await context.sendMessage({ preventDefault() {} });
  assert.equal(requests[1].body.provider, "openrouter_free");
  assert.equal(requests[1].body.allow_remote, true);

  elements.sendButton.disabled = false;
  const image = { media_type: "image/png", data: pngData };
  images.push(image);
  await context.sendMessage({ preventDefault() {} });
  assert.equal(requests[2].body.content, "Describe the attached image.");
  assert.equal(requests[2].body.images[0], image);
  assert.equal(requests[2].body.allow_remote, true);
  assert.equal(images.length, 0);
});

test("sending follows the live reply and lets the reader scroll up", async () => {
  const renderer = await read("renderer/renderer.js");
  let onStreamEvent;
  let reply;
  let text = "";
  const list = {
    scrollTop: 100,
    scrollHeight: 1000,
    clientHeight: 300,
    contains: (node) => node === reply,
    replaceChildren() {
      this.scrollTop = 0;
      this.scrollHeight = 0;
    },
  };
  reply = {
    get textContent() { return text; },
    set textContent(value) {
      text = value;
      list.scrollHeight += 100;
    },
  };
  const elements = { messageInput: { value: "Hello" }, messageList: list, sendButton: {}, chatStatus: {} };
  const state = {
    selectedBranchId: "branch",
    selectionSequence: 1,
    selectedProviderId: "ollama",
    providers: [{ id: "ollama", is_remote: false }],
  };
  const context = {
    elements, state,
    selectedModel: () => "tiny",
    chatImages: { payload: () => [], reset: () => {} },
    api: async () => ({ items: Array.from({ length: 5 }, () => ({ role: "user", content: "Hello" })) }),
    appendMessage: (role) => {
      list.scrollHeight += 100;
      return role === "assistant" ? reply : {};
    },
    window: { cog: { stream: (_path, _request, handler) => { onStreamEvent = handler; } } },
  };
  const helpers = renderer.slice(renderer.indexOf("function scrollChatToBottom()"), renderer.indexOf("function appendMessage("));
  const loadCode = renderer.slice(renderer.indexOf("async function loadMessages("), renderer.indexOf("async function selectConversation("));
  const sendCode = renderer.slice(renderer.indexOf("async function sendMessage("), renderer.indexOf("const views ="));
  runInNewContext(helpers + loadCode + sendCode, context);

  await context.sendMessage({ preventDefault() {} });
  assert.equal(list.scrollTop, 1200);
  list.scrollTop = list.scrollHeight - list.clientHeight;
  await onStreamEvent("token", { token: "one" });
  assert.equal(list.scrollTop, 1300);
  list.scrollTop = 150;
  await onStreamEvent("token", { token: " two" });
  assert.equal(list.scrollHeight, 1400);
  assert.equal(list.scrollTop, 150);
  await onStreamEvent("done", { run_id: "run" });
  assert.equal(list.scrollHeight, 500);
  assert.equal(list.scrollTop, 150);
});

test("image attachments detect bytes, enforce size, and reject renamed SVG files", async () => {
  const bytes = Buffer.from(pngData, "base64");
  const png = new File([bytes], "photo.png");
  assert.deepEqual(await readChatImage(png), {
    name: "photo.png",
    size: bytes.length,
    media_type: "image/png",
    data: pngData,
  });
  await assert.rejects(
    readChatImage(new File(["<svg></svg>"], "vector.png", { type: "image/png" })),
    /must be a PNG, JPEG, or WebP/,
  );
  await assert.rejects(
    readChatImage(new File([new Uint8Array(4 * 1024 * 1024 + 1)], "oversized.png")),
    /exceeds 4 MiB/,
  );
});

test("selected file text is previewable, bounded, and rejects binary data", async () => {
  const html = await read("renderer/index.html");
  assert.match(html, /<input id="chat-file" type="file"/);
  const fixture = new File(["local reference"], "note.txt");
  assert.equal(await readSelectedTextFile(fixture), "File: note.txt\n\nlocal reference");
  const oversized = new File(["a".repeat(11_999), "🌻", "b"], "long.txt");
  const excerpt = await readSelectedTextFile(oversized);
  assert.equal(excerpt, `File: long.txt\n\n${"a".repeat(11_999)}\n\n[Excerpt truncated]`);
  await assert.rejects(readSelectedTextFile(new File([Uint8Array.of(0, 1)], "data.bin")), /UTF-8 text file/);
});

test("Explorer tools accept only scoped window and immediate subfolder requests", async () => {
  const main = await read("main/main.js");
  assert.match(main, /ipcMain\.handle\("cog:explorer", \(event, request\) => \{\s*assertTrustedSender\(event\)/);

  const window = { window_id: "123", folder: "C:\\Project" };
  assert.deepEqual(validateExplorerRequest({ action: "list", folder: "C:\\Ignored" }), { action: "list" });
  assert.deepEqual(validateExplorerRequest({ action: "inspect", ...window }), { action: "inspect", ...window });
  assert.deepEqual(
    validateExplorerRequest({ action: "open_child", ...window, child: "Notes" }),
    { action: "open_child", ...window, child: "Notes" },
  );
  assert.throws(() => validateExplorerRequest({ action: "delete", ...window }), /File Explorer tool/);
  assert.throws(() => validateExplorerRequest({
    action: "inspect", window_id: "123", folder: "\\\\server\\share",
  }), /open File Explorer window/);
  for (const child of ["..", "one\\two", "C:\\Another", "Notes."]) {
    assert.throws(() => validateExplorerRequest({ action: "open_child", ...window, child }), /subfolder/);
  }
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
