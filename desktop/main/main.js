import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { BackendSupervisor } from "./backend-supervisor.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const desktopRoot = path.resolve(here, "..");
const repositoryRoot = path.resolve(desktopRoot, "..");
const allowedExternalHosts = new Set([
  "github.com",
  "ollama.com",
  "platform.openai.com",
  "openai.com",
]);

app.setName("CognitivePlatform");

const supervisor = new BackendSupervisor({
  repoRoot: repositoryRoot,
  backendDir: path.join(repositoryRoot, "backend"),
  dataDir: app.getPath("userData"),
  onFatal: (error) => {
    dialog.showErrorBox(
      "SMH-Tree backend stopped",
      `The local backend could not be started or restarted.\n\n${error.message}`,
    );
    app.quit();
  },
});

function registerIpcHandlers() {
  ipcMain.handle("cog:get-api-base", () => supervisor.connection?.baseUrl ?? null);

  ipcMain.handle("cog:request", async (_event, request) => {
    const connection = supervisor.connection;
    if (!connection) throw new Error("The local backend is not connected.");

    const requestPath = request?.path;
    if (
      typeof requestPath !== "string" ||
      !requestPath.startsWith("/v1/") ||
      requestPath.startsWith("//")
    ) {
      throw new Error("Only relative /v1 API paths are permitted.");
    }

    const method = String(request.method ?? "GET").toUpperCase();
    if (!new Set(["GET", "POST", "PATCH", "DELETE"]).has(method)) {
      throw new Error("Unsupported API method.");
    }

    const url = new URL(requestPath, connection.baseUrl);
    if (url.origin !== connection.baseUrl || !url.pathname.startsWith("/v1/")) {
      throw new Error("The request must remain within the local API.");
    }

    const headers = { Authorization: `Bearer ${connection.token}` };
    const options = { method, headers, signal: AbortSignal.timeout(30_000) };
    if (request.body !== undefined) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(request.body);
    }

    const response = await fetch(url, options);
    const raw = await response.text();
    let data = raw;
    try {
      data = raw ? JSON.parse(raw) : null;
    } catch {
      // Preserve non-JSON responses as text.
    }
    return { status: response.status, ok: response.ok, data };
  });

  ipcMain.handle("cog:open-external", async (_event, rawUrl) => {
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
  void window.loadFile(path.join(desktopRoot, "renderer/index.html"));
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
  registerIpcHandlers();
  await supervisor.start();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
}).catch((error) => {
  dialog.showErrorBox(
    "SMH-Tree could not start",
    `Could not start the local backend. Ensure uv and Python 3.12 are installed for this development build.\n\n${error.message}`,
  );
  void supervisor.stop().finally(() => app.quit());
});
