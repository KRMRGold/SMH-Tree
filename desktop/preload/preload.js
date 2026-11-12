import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("cog", Object.freeze({
  getApiBase: () => ipcRenderer.invoke("cog:get-api-base"),
  request: (path, options = {}) => ipcRenderer.invoke("cog:request", {
    path,
    method: options.method ?? "GET",
    body: options.body,
    providerId: options.providerId,
  }),
  stream: (path, options = {}, onEvent = () => {}) => {
    if (typeof onEvent !== "function") {
      throw new TypeError("onEvent must be a function.");
    }
    const channel = new MessageChannel();
    channel.port1.onmessage = ({ data }) => {
      if (data.type === "event") onEvent(data.event, data.data);
      else if (data.type === "error") onEvent("error", data);
      else if (data.type === "done") channel.port1.close();
    };
    channel.port1.start();
    ipcRenderer.postMessage("cog:stream", {
      path,
      method: options.method ?? "POST",
      body: options.body,
      providerId: options.providerId,
    }, [channel.port2]);
    return () => channel.port1.close();
  },
  openExternal: (url) => ipcRenderer.invoke("cog:open-external", url),
  setProviderApiKey: (providerId, value) => ipcRenderer.invoke("cog:set-provider-api-key", { providerId, value }),
  deleteProviderApiKey: (providerId) => ipcRenderer.invoke("cog:delete-provider-api-key", providerId),
  hasProviderApiKey: (providerId) => ipcRenderer.invoke("cog:has-provider-api-key", providerId),
}));
