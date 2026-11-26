import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export function validateExplorerRequest(request) {
  const action = request?.action;
  if (action === "list") return { action };
  if (action !== "inspect" && action !== "open_child") {
    throw new Error("Choose a File Explorer tool.");
  }
  const { window_id, folder, child } = request;
  if (typeof window_id !== "string" || !/^\d{1,20}$/.test(window_id) ||
      typeof folder !== "string" || folder.length > 2048 || !/^[a-z]:\\/i.test(folder) ||
      /[\x00-\x1f]/.test(folder)) {
    throw new Error("Select an open File Explorer window.");
  }
  if (action === "inspect") return { action, window_id, folder };
  if (typeof child !== "string" || !child.length || child.length > 255 ||
      /[\\/:*?"<>|\x00-\x1f]/.test(child) || /[. ]$/.test(child)) {
    throw new Error("Choose a subfolder from the current listing.");
  }
  return { action, window_id, folder, child };
}

export async function runExplorerTool(request) {
  if (process.platform !== "win32") throw new Error("File Explorer tools require Windows.");
  const payload = validateExplorerRequest(request);
  const scriptPath = fileURLToPath(new URL("./window-explorer.ps1", import.meta.url));
  const script = await readFile(scriptPath, "utf8");
  const powershell = path.join(
    process.env.SystemRoot ?? "C:\\Windows", "System32", "WindowsPowerShell", "v1.0", "powershell.exe",
  );

  const output = await new Promise((resolve, reject) => {
    const child = execFile(
      powershell,
      ["-NoLogo", "-NoProfile", "-NonInteractive", "-STA", "-Command", script],
      { windowsHide: true, timeout: 10_000, maxBuffer: 256 * 1024, encoding: "utf8" },
      (error, stdout) => {
        if (error) reject(new Error("The File Explorer operation could not complete."));
        else resolve(stdout);
      },
    );
    child.stdin.on("error", () => {});
    child.stdin.end(JSON.stringify(payload));
  });

  let result;
  try {
    result = JSON.parse(output.trim());
  } catch {
    throw new Error("File Explorer returned an unreadable result.");
  }
  if (typeof result?.error === "string") throw new Error(result.error);
  return result;
}
