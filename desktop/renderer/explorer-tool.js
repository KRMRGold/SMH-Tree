import { addReferenceToMessage } from "./chat-tools.js";

export function bindExplorerTool({ messageInput, getSelectionSequence }) {
  const byId = (id) => document.getElementById(id);
  const dialog = byId("explorer-tool-dialog");
  const windows = byId("explorer-windows");
  const inspect = byId("inspect-explorer-folder");
  const refresh = byId("refresh-explorer-windows");
  const preview = byId("explorer-preview");
  const previewLabel = byId("explorer-preview-label");
  const childFields = byId("explorer-child-fields");
  const child = byId("explorer-child");
  const openChild = byId("open-explorer-child");
  const add = byId("add-explorer-listing");
  const status = byId("explorer-tool-status");
  let candidates = [];
  let listing = null;
  let busy = false;
  let revision = 0;
  let selectionSequence = null;

  function showStatus(message) {
    status.textContent = message;
    status.hidden = !message;
  }

  function active() {
    return dialog.open && selectionSequence === getSelectionSequence();
  }

  function selectedWindow() {
    return windows.value === "" ? null : candidates[Number(windows.value)];
  }

  function updateControls() {
    windows.disabled = busy || candidates.length === 0;
    refresh.disabled = busy;
    inspect.disabled = busy || !selectedWindow();
    child.disabled = busy;
    openChild.disabled = busy || !listing || !child.value;
    add.disabled = busy || !listing;
  }

  function clearListing() {
    listing = null;
    preview.value = "";
    preview.hidden = true;
    previewLabel.hidden = true;
    childFields.hidden = true;
    child.replaceChildren();
    add.hidden = true;
  }

  function showWindows(selectedIndex = "") {
    const placeholder = new Option("Choose a File Explorer window", "");
    placeholder.disabled = true;
    windows.replaceChildren(placeholder, ...candidates.map((window, index) =>
      new Option(`${window.title || "File Explorer"} · ${window.folder}`, String(index))
    ));
    windows.value = selectedIndex;
  }

  function showListing(result) {
    const selectedIndex = windows.value;
    candidates[Number(selectedIndex)] = result.window;
    showWindows(selectedIndex);
    listing = result;
    const lines = result.entries.map((entry) => `${entry.is_folder ? "[Folder] " : ""}${entry.name}`);
    if (!lines.length) lines.push("This folder is empty.");
    if (result.truncated) lines.push("[More items in this folder]");
    preview.value = `File Explorer folder: ${result.window.folder}\n\n${lines.join("\n")}`;
    preview.hidden = false;
    previewLabel.hidden = false;
    add.hidden = false;
    const folders = result.entries.filter((entry) => entry.is_folder);
    const placeholder = new Option("Choose a subfolder", "");
    placeholder.disabled = true;
    child.replaceChildren(placeholder, ...folders.map((entry) => new Option(entry.name, entry.name)));
    child.value = "";
    childFields.hidden = folders.length === 0;
  }

  async function perform(request, onSuccess) {
    if (!active() || busy) return;
    const requestRevision = ++revision;
    busy = true;
    updateControls();
    showStatus("Waiting for File Explorer…");
    try {
      const result = await window.cog.explorer(request);
      if (!active() || revision !== requestRevision) return;
      showStatus("");
      onSuccess(result);
    } catch (error) {
      if (active() && revision === requestRevision) {
        showStatus(error.message.replace(/^Error invoking remote method '[^']+': Error: /, ""));
      }
    } finally {
      if (active() && revision === requestRevision) {
        busy = false;
        updateControls();
      }
    }
  }

  function refreshWindows() {
    if (busy) return;
    clearListing();
    void perform({ action: "list" }, (result) => {
      candidates = result.windows;
      showWindows();
      if (!candidates.length) showStatus("Open a local folder in File Explorer, then click Refresh.");
    });
  }

  byId("open-explorer-tool").addEventListener("click", () => {
    selectionSequence = getSelectionSequence();
    revision += 1;
    busy = false;
    candidates = [];
    showWindows();
    dialog.showModal();
    refreshWindows();
  });
  byId("close-explorer-tool").addEventListener("click", () => dialog.close());
  refresh.addEventListener("click", refreshWindows);
  windows.addEventListener("change", () => {
    clearListing();
    showStatus("");
    updateControls();
  });
  child.addEventListener("change", updateControls);

  inspect.addEventListener("click", () => {
    const window = selectedWindow();
    if (!window) return;
    clearListing();
    void perform({ action: "inspect", window_id: window.window_id, folder: window.folder }, showListing);
  });
  openChild.addEventListener("click", () => {
    if (!listing || !child.value) return;
    const { window_id, folder } = listing.window;
    void perform({ action: "open_child", window_id, folder, child: child.value }, showListing);
  });
  add.addEventListener("click", () => {
    if (!active() || busy || !listing) return;
    try {
      addReferenceToMessage(messageInput, dialog, preview.value);
    } catch (error) {
      showStatus(error.message);
    }
  });
}
