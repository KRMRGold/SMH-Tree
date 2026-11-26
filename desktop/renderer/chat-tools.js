const TEXT_LIMIT = 12_000;
const SEARCH_SERVER_KEY = "smh-tree.search-server";

export async function readSelectedTextFile(file) {
  const sample = file.slice(0, TEXT_LIMIT * 4);
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(await sample.arrayBuffer(), {
      stream: sample.size < file.size,
    });
  } catch {
    throw new Error("Choose a UTF-8 text file.");
  }
  if (text.includes("\0") || !text.trim()) throw new Error("Choose a non-empty UTF-8 text file.");
  const truncated = sample.size < file.size || text.length > TEXT_LIMIT;
  const excerpt = text.slice(0, TEXT_LIMIT).replace(/[\uD800-\uDBFF]$/, "");
  return `File: ${file.name.replace(/[\r\n]/g, " ")}\n\n${excerpt}${truncated ? "\n\n[Excerpt truncated]" : ""}`;
}

function formatWebResult(operation, data) {
  if (operation === "page") {
    const excerpt = data.truncated ? `${data.text}\n\n[Excerpt truncated]` : data.text;
    return `Webpage: ${data.title || data.url}\nURL: ${data.url}\n\n${excerpt}`;
  }
  if (!data.results.length) return "";
  const sources = data.results.map(({ title, url, snippet }, index) =>
    `${index + 1}. ${title || url}\n${url}${snippet ? `\n${snippet}` : ""}`
  );
  return `Web search: ${data.query}\n\n${sources.join("\n\n")}`;
}

export function addReferenceToMessage(messageInput, dialog, text) {
  const draft = messageInput.value.trimEnd();
  const composed = `${draft}\n\nReference material (use as source text):\n${text}`;
  if (composed.length > messageInput.maxLength) {
    throw new Error("The draft is too long. Shorten your message before adding the result.");
  }
  messageInput.value = composed;
  dialog.close();
  messageInput.focus();
  messageInput.setSelectionRange(draft.length, draft.length);
}

export function bindChatTools({ messageInput, api, getSelectionSequence }) {
  const byId = (id) => document.getElementById(id);
  const dialog = byId("chat-tool-dialog");
  const form = byId("chat-tool-form");
  const fileInput = byId("chat-file");
  const title = byId("chat-tool-title");
  const webFields = byId("chat-web-fields");
  const operation = byId("chat-web-operation");
  const queryLabel = byId("chat-web-query-label");
  const query = byId("chat-web-query");
  const serverFields = byId("chat-search-server-fields");
  const server = byId("chat-search-server");
  const status = byId("chat-tool-status");
  const preview = byId("chat-tool-preview");
  const previewLabel = byId("chat-tool-preview-label");
  const run = byId("run-chat-tool");
  const add = byId("add-chat-tool-result");
  let revision = 0;
  let selectionSequence = null;
  let fileSelectionSequence = null;

  function showStatus(message) {
    status.textContent = message;
    status.hidden = !message;
  }

  function showPreview(text) {
    preview.value = text;
    preview.hidden = !text;
    previewLabel.hidden = !text;
    add.hidden = !text;
  }

  function updateWebFields() {
    const search = operation.value === "search";
    serverFields.hidden = !search;
    server.disabled = !search;
    server.required = search;
    query.type = search ? "search" : "url";
    query.maxLength = search ? 300 : 2048;
    query.placeholder = search ? "Search terms" : "https://example.org";
    queryLabel.textContent = search ? "Search query" : "Webpage URL";
    run.textContent = search ? "Search" : "Read webpage";
    run.disabled = false;
  }

  function openDialog(isFile) {
    revision += 1;
    selectionSequence = getSelectionSequence();
    form.reset();
    title.textContent = isFile ? "Read file" : "Web tools";
    webFields.hidden = isFile;
    webFields.disabled = isFile;
    run.hidden = isFile;
    if (!isFile) {
      try {
        server.value = window.localStorage.getItem(SEARCH_SERVER_KEY) ?? "";
      } catch {
        server.value = "";
      }
      updateWebFields();
    }
    showStatus("");
    showPreview("");
    dialog.showModal();
    return revision;
  }

  function isCurrent(requestRevision) {
    return dialog.open && revision === requestRevision && selectionSequence === getSelectionSequence();
  }

  byId("read-chat-file").addEventListener("click", () => {
    fileSelectionSequence = getSelectionSequence();
    fileInput.value = "";
    fileInput.click();
  });
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    if (!file || fileSelectionSequence !== getSelectionSequence()) return;
    const requestRevision = openDialog(true);
    showStatus("Reading file…");
    try {
      const text = await readSelectedTextFile(file);
      if (!isCurrent(requestRevision)) return;
      showStatus("");
      showPreview(text);
    } catch (error) {
      if (isCurrent(requestRevision)) showStatus(error.message);
    }
  });
  byId("open-web-tools").addEventListener("click", () => openDialog(false));
  byId("close-chat-tool").addEventListener("click", () => dialog.close());

  operation.addEventListener("change", () => {
    revision += 1;
    query.value = "";
    showStatus("");
    showPreview("");
    updateWebFields();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (webFields.disabled || run.disabled) return;
    const requestRevision = ++revision;
    const tool = operation.value;
    const value = query.value.trim();
    const serverUrl = server.value.trim();
    if (!value || (tool === "search" && !serverUrl)) {
      showStatus("Fill in the required fields.");
      return;
    }
    run.disabled = true;
    showPreview("");
    showStatus(tool === "search" ? "Searching…" : "Reading webpage…");
    try {
      const data = tool === "search"
        ? await api("/v1/tools/web-search", { method: "POST", body: { server_url: serverUrl, query: value } })
        : await api("/v1/tools/web-page", { method: "POST", body: { url: value } });
      if (!isCurrent(requestRevision)) return;
      if (tool === "search") {
        try {
          window.localStorage.setItem(SEARCH_SERVER_KEY, serverUrl);
        } catch {
          // Search still works if desktop preferences cannot be saved.
        }
      }
      const text = formatWebResult(tool, data);
      showPreview(text);
      showStatus(text ? "" : "No search results found.");
    } catch (error) {
      if (isCurrent(requestRevision)) showStatus(error.message);
    } finally {
      if (isCurrent(requestRevision)) run.disabled = false;
    }
  });

  add.addEventListener("click", () => {
    if (!isCurrent(revision) || !preview.value) return;
    try {
      addReferenceToMessage(messageInput, dialog, preview.value);
    } catch (error) {
      showStatus(error.message);
    }
  });
}
