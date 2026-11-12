import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("cog", Object.freeze({
  getApiBase: () => ipcRenderer.invoke("cog:get-api-base"),
  request: (path, options = {}) => ipcRenderer.invoke("cog:request", {
    path,
    method: options.method ?? "GET",
    body: options.body,
  }),
  openExternal: (url) => ipcRenderer.invoke("cog:open-external", url),
}));
