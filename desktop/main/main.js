import { app, BrowserWindow, dialog, ipcMain, safeStorage, shell } from "electron";
import { spawn } from "node:child_process";
import { access, mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import { setTimeout as delay } from "node:timers/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { BackendSupervisor } from "./backend-supervisor.js";
import { runExplorerTool } from "./explorer-tools.js";
import { createSseParser } from "./sse-parser.js";

const squirrelStartup = app.isPackaged && process.platform === "win32" &&
  (await import("electron-squirrel-startup")).default;

if (app.isPackaged) {
  // Keep existing development-build data and credentials available after installation.
  const profile = app.commandLine.getSwitchValue("user-data-dir");
  app.setPath("userData", profile || path.join(app.getPath("appData"), "smh-tree-desktop"));
}

const here = path.dirname(fileURLToPath(import.meta.url));
const desktopRoot = path.resolve(here, "..");
const repositoryRoot = path.resolve(desktopRoot, "..");
const rendererPath = path.join(desktopRoot, "renderer/index.html");
const rendererUrl = pathToFileURL(rendererPath).href;
const providerKeysPath = path.join(app.getPath("userData"), "provider-keys.enc");

function assertSecureStorageAvailable() {
  if (!safeStorage.isEncryptionAvailable()) throw new Error("OS-backed secure storage is unavailable.");
  if (safeStorage.getSelectedStorageBackend?.() === "basic_text") {
    throw new Error("Secure credential storage is unavailable. Configure an OS keyring before saving remote API keys.");
  }
}
async function readProviderKeys() {
  let encrypted;
  try {
    encrypted = await readFile(providerKeysPath);
  } catch (error) {
    if (error.code === "ENOENT") return {};
    throw error;
  }
  assertSecureStorageAvailable();
  return JSON.parse(safeStorage.decryptString(encrypted));
}
function validProviderId(value) {
  if (typeof value !== "string" || !/^[a-zA-Z0-9_-]{1,80}$/.test(value)) throw new Error("Invalid provider identifier.");
  return value;
}
async function providerKey(providerId) {
  if (!providerId) return null;
  const keys = await readProviderKeys();
  return keys[validProviderId(providerId)] ?? null;
}
async function writeProviderKeys(keys) {
  assertSecureStorageAvailable();
  await mkdir(path.dirname(providerKeysPath), { recursive: true });
  const temporaryPath = `${providerKeysPath}.tmp`;
  await writeFile(temporaryPath, safeStorage.encryptString(JSON.stringify(keys)), { mode: 0o600 });
  await rename(temporaryPath, providerKeysPath);
}
const allowedExternalHosts = new Set([
  "github.com",
  "ollama.com",
  "platform.openai.com",
  "openai.com",
]);

app.setName("CognitivePlatform");

const packagedBackend = app.isPackaged ? path.join(process.resourcesPath, "cogplat") : null;
const supervisor = new BackendSupervisor({
  repoRoot: packagedBackend ?? repositoryRoot,
  backendDir: packagedBackend ?? path.join(repositoryRoot, "backend"),
  dataDir: app.getPath("userData"),
  ...(packagedBackend && {
    command: path.join(packagedBackend, "cogplat.exe"),
    argsFactory: ({ port }) => ["--host", "127.0.0.1", "--port", String(port)],
  }),
  onFatal: (error) => {
    dialog.showErrorBox(
      "SMH-Tree backend stopped",
      `The local backend could not be started or restarted.\n\n${error.message}`,
    );
    app.quit();
  },
});

function assertTrustedSender(event) {
  if (
    !event.senderFrame ||
    event.senderFrame !== event.sender.mainFrame ||
    event.senderFrame.url !== rendererUrl
  ) {
    throw new Error("Untrusted renderer frame.");
  }
}

function buildApiUrl(connection, requestPath) {
  if (
    typeof requestPath !== "string" ||
    !requestPath.startsWith("/v1/") ||
    requestPath.startsWith("//")
  ) {
    throw new Error("Only relative /v1 API paths are permitted.");
  }
  const url = new URL(requestPath, connection.baseUrl);
  if (url.origin !== connection.baseUrl || !url.pathname.startsWith("/v1/")) {
    throw new Error("The request must remain within the local API.");
  }
  return url;
}

function requestMethod(request, allowDelete = true) {
  const method = String(request?.method ?? "GET").toUpperCase();
  const allowed = allowDelete ? ["GET", "POST", "PATCH", "DELETE"] : ["GET", "POST"];
  if (!allowed.includes(method)) throw new Error("Unsupported API method.");
  return method;
}

const defaultOllamaUrl = "http://127.0.0.1:11434";
const ollamaUrl = (process.env.COGPLAT_OLLAMA_BASE_URL ?? defaultOllamaUrl).trim().replace(/\/+$/, "") || defaultOllamaUrl;
let ollamaStartup;

async function requestOllama(endpoint, body) {
  const options = { signal: AbortSignal.timeout(body ? 120_000 : 2_000) };
  if (body) {
    options.method = "POST";
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  const response = await fetch(`${ollamaUrl}/api/${endpoint}`, options);
  if (!response.ok) throw new Error(`Ollama returned HTTP ${response.status}.`);
  return response.json();
}

async function startInstalledOllama() {
  try {
    await requestOllama("version");
    return;
  } catch {
    if (process.platform !== "win32" ||
        ![defaultOllamaUrl, "http://localhost:11434"].includes(ollamaUrl)) {
      throw new Error("The configured Ollama service is unreachable.");
    }
  }

  const installDir = process.env.LOCALAPPDATA
    ? path.join(process.env.LOCALAPPDATA, "Programs", "Ollama")
    : null;
  const candidates = [];
  if (installDir) {
    candidates.push([path.join(installDir, "ollama app.exe"), []]);
    candidates.push([path.join(installDir, "ollama.exe"), ["serve"]]);
  }
  for (const entry of (process.env.PATH ?? "").split(path.delimiter)) {
    const directory = entry.replace(/^"|"$/g, "");
    if (path.isAbsolute(directory)) candidates.push([path.join(directory, "ollama.exe"), ["serve"]]);
  }

  let executable;
  for (const candidate of candidates) {
    try {
      await access(candidate[0]);
      executable = candidate;
      break;
    } catch {
      // Continue looking for a local Ollama installation.
    }
  }
  if (!executable) throw new Error("Ollama was not found. Install Ollama for Windows, then try again.");

  const [command, args] = executable;
  await new Promise((resolve, reject) => {
    const child = spawn(command, args, { detached: true, windowsHide: true, stdio: "ignore" });
    child.once("error", reject);
    child.once("spawn", () => {
      child.unref();
      resolve();
    });
  });
  for (let attempt = 0; attempt < 20; attempt += 1) {
    try {
      await requestOllama("version");
      return;
    } catch {
      await delay(500);
    }
  }
  throw new Error("Ollama started but its API did not become reachable.");
}

function ensureOllama() {
  ollamaStartup ??= startInstalledOllama().finally(() => { ollamaStartup = null; });
  return ollamaStartup;
}

function registerIpcHandlers() {
  ipcMain.handle("cog:explorer", (event, request) => {
    assertTrustedSender(event);
    return runExplorerTool(request);
  });
  ipcMain.handle("cog:start-ollama", async (event) => {
    assertTrustedSender(event);
    await ensureOllama();
  });
  ipcMain.handle("cog:load-ollama-model", async (event, model) => {
    assertTrustedSender(event);
    if (typeof model !== "string" || !model.trim() || model.length > 200) {
      throw new Error("Choose an installed Ollama model.");
    }
    await ensureOllama();
    const { models } = await requestOllama("tags");
    if (!models?.some((item) => item.name === model)) {
      throw new Error("That model is not in Ollama’s installed model list.");
    }
    await requestOllama("generate", { model, stream: false });
  });
  ipcMain.handle("cog:set-provider-api-key", async (event, payload) => {
    assertTrustedSender(event);
    const providerId = validProviderId(payload?.providerId);
    const value = payload?.value;
    if (typeof value !== "string" || value.length > 8000) throw new Error("Invalid API key value.");
    const keys = await readProviderKeys();
    if (value.trim()) keys[providerId] = value.trim();
    else delete keys[providerId];
    await writeProviderKeys(keys);
    return true;
  });
  ipcMain.handle("cog:delete-provider-api-key", async (event, providerId) => {
    assertTrustedSender(event);
    const keys = await readProviderKeys();
    delete keys[validProviderId(providerId)];
    if (Object.keys(keys).length) await writeProviderKeys(keys);
    else await unlink(providerKeysPath).catch((error) => { if (error.code !== "ENOENT") throw error; });
    return true;
  });
  ipcMain.handle("cog:has-provider-api-key", async (event, providerId) => {
    assertTrustedSender(event);
    const keys = await readProviderKeys();
    return Boolean(keys[validProviderId(providerId)]);
  });

  ipcMain.handle("cog:get-secure-storage-status", (event) => {
    assertTrustedSender(event);
    const backend = safeStorage.isEncryptionAvailable() ? safeStorage.getSelectedStorageBackend?.() ?? "unknown" : "unavailable";
    return { available: safeStorage.isEncryptionAvailable(), backend, secure: backend !== "basic_text" && backend !== "unavailable" };
  });

  ipcMain.handle("cog:get-data-directory", (event) => {
    assertTrustedSender(event);
    return app.getPath("userData");
  });

  ipcMain.handle("cog:get-api-base", (event) => {
    assertTrustedSender(event);
    return supervisor.connection?.baseUrl ?? null;
  });

  ipcMain.handle("cog:request", async (event, request) => {
    assertTrustedSender(event);
    const connection = supervisor.connection;
    if (!connection) throw new Error("The local backend is not connected.");

    const url = buildApiUrl(connection, request?.path);
    const method = requestMethod(request);
    const headers = { Authorization: `Bearer ${connection.token}` };
    const apiKey = await providerKey(request?.providerId);
    if (apiKey) headers["X-Provider-API-Key"] = apiKey;
    const isExtraction = method === "POST" && /^\/v1\/messages\/[^/]+\/extract-claims$/.test(url.pathname);
    const options = { method, headers, signal: AbortSignal.timeout(isExtraction ? 150_000 : 30_000) };
    if (request.body !== undefined) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(request.body);
    }

    let response;
    let raw;
    try {
      response = await fetch(url, options);
      raw = await response.text();
    } catch (error) {
      if (!isExtraction) throw error;
      const timedOut = options.signal.aborted;
      return {
        ok: false,
        status: timedOut ? 504 : 502,
        data: { error: { message: timedOut
          ? "Extraction timed out. Check Claims for results before trying again."
          : "The local backend connection was interrupted. Check Claims before trying again." } },
      };
    }
    let data = raw;
    try {
      data = raw ? JSON.parse(raw) : null;
    } catch {
      // Preserve non-JSON responses as text.
    }
    return { status: response.status, ok: response.ok, data };
  });

  ipcMain.on("cog:stream", (event, request) => {
    let port;
    try {
      assertTrustedSender(event);
      port = event.ports[0];
      if (!port) throw new Error("A stream message port is required.");
    } catch {
      port?.close();
      return;
    }

    const controller = new AbortController();
    port.on("close", () => controller.abort());

    void (async () => {
      try {
        const connection = supervisor.connection;
        if (!connection) throw new Error("The local backend is not connected.");
        const url = buildApiUrl(connection, request?.path);
        const method = requestMethod(request, false);
        const headers = { Authorization: `Bearer ${connection.token}` };
        const apiKey = await providerKey(request?.providerId);
        if (apiKey) headers["X-Provider-API-Key"] = apiKey;
        const options = { method, headers, signal: controller.signal };
        if (request?.body !== undefined) {
          headers["Content-Type"] = "application/json";
          options.body = JSON.stringify(request.body);
        }

        const response = await fetch(url, options);
        if (!response.ok) {
          const detail = await response.text();
          port.postMessage({
            type: "error",
            status: response.status,
            message: detail.slice(0, 2000) || "The stream request failed.",
          });
          return;
        }
        if (!response.body) throw new Error("The backend returned no response stream.");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const parser = createSseParser((eventName, data) => {
          port.postMessage({ type: "event", event: eventName, data });
        });

        while (!controller.signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          parser.push(decoder.decode(value, { stream: true }));
        }
        parser.push(decoder.decode());
        parser.end();
        if (!controller.signal.aborted) port.postMessage({ type: "done" });
      } catch (error) {
        if (!controller.signal.aborted) {
          port.postMessage({ type: "error", message: error.message || "Stream failed." });
        }
      } finally {
        port.close();
      }
    })();
  });

  ipcMain.handle("cog:open-external", async (event, rawUrl) => {
    assertTrustedSender(event);
    let url;
    try {
      url = new URL(rawUrl);
    } catch {
      throw new Error("Invalid external URL.");
    }
    if (url.protocol !== "https:" || !allowedExternalHosts.has(url.hostname)) {
      throw new Error("This external destination is not allowlisted.");
    }
    await shell.openExternal(url.toString());
    return true;
  });
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 960,
    minHeight: 640,
    backgroundColor: "#111018",
    webPreferences: {
      preload: path.join(here, "../preload/preload.js"),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      webSecurity: true,
    },
  });

  window.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  window.webContents.on("will-navigate", (event) => event.preventDefault());
  void window.loadFile(rendererPath);
  return window;
}

let quitting = false;
app.on("before-quit", (event) => {
  if (quitting) return;
  event.preventDefault();
  quitting = true;
  void supervisor.stop().finally(() => app.quit());
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.whenReady().then(async () => {
  if (squirrelStartup) {
    app.quit();
    return;
  }
  registerIpcHandlers();
  await supervisor.start();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
}).catch((error) => {
  dialog.showErrorBox(
    "SMH-Tree could not start",
    app.isPackaged
      ? `Could not start the bundled backend.\n\n${error.message}`
      : `Could not start the local backend. Ensure uv and Python 3.12 are installed for this development build.\n\n${error.message}`,
  );
  void supervisor.stop().finally(() => app.quit());
});
