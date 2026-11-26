import { bindChatImages } from "./chat-images.js";
import { bindChatTools } from "./chat-tools.js";
import { bindExplorerTool } from "./explorer-tool.js";

const $ = (selector) => document.querySelector(selector);

const elements = {
  status: $("#connection-status"),
  statusDot: $("#status-dot"),
  projectSelect: $("#project-select"),
  conversationList: $("#conversation-list"),
  newProject: $("#new-project"),
  newConversation: $("#new-conversation"),
  activeTitle: $("#active-title"),
  providerSelect: $("#provider-select"),
  modelName: $("#model-name"),
  ollamaModel: $("#ollama-model"),
  openrouterModel: $("#openrouter-model"),
  emptyState: $("#empty-state"),
  chatPanel: $("#chat-panel"),
  messageList: $("#message-list"),
  chatStatus: $("#chat-status"),
  composer: $("#composer"),
  messageInput: $("#message-input"),
  sendButton: $("#send-button"),
};

const state = {
  projects: [],
  conversations: [],
  providers: [],
  selectedProjectId: "",
  selectedConversationId: null,
  selectedBranchId: null,
  selectedProviderId: null,
  cancelStream: null,
  lastRunId: null,
  currentView: "chat",
  selectionSequence: 0,
  conversationsRequestSequence: 0,
  contextRequestSequence: 0,
  memoryRequestSequence: 0,
  claims: [],
};

const chatImages = bindChatImages({
  panel: elements.chatPanel,
  composer: elements.composer,
  picker: $("#chat-image-picker"),
  attach: $("#attach-chat-image"),
  previews: $("#chat-image-previews"),
  status: $("#chat-image-status"),
  remote: $("#chat-image-remote"),
  getProvider: () => state.providers.find((provider) => provider.id === state.selectedProviderId),
  canAttach: () => Boolean(state.selectedBranchId) && !elements.chatPanel.hidden,
});

function setConnectionStatus(message, stateName = "ready") {
  elements.status.textContent = message;
  elements.statusDot.dataset.state = stateName;
}

async function api(path, options) {
  const response = await window.cog.request(path, options);
  if (!response.ok) {
    const message = response.data?.error?.message ?? response.data?.detail?.message ?? "The request failed.";
    throw new Error(message);
  }
  return response.data;
}

function makeOption(value, label) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  return option;
}

function scrollChatToBottom() {
  elements.messageList.scrollTop = elements.messageList.scrollHeight;
}

function isChatNearBottom() {
  const { scrollHeight, scrollTop, clientHeight } = elements.messageList;
  return scrollHeight - scrollTop - clientHeight <= 48;
}

function appendMessage(role, content, participant = role, savedMessageId = null) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = participant || role;

  const body = document.createElement("div");
  body.className = "message-content";
  body.textContent = content ?? "";

  article.append(meta, body);
  if (savedMessageId && (role === "user" || role === "assistant") && content?.trim()) {
    const conversation = state.conversations.find((item) => item.id === state.selectedConversationId);
    const projectId = conversation?.project_id || state.selectedProjectId || "";
    const actions = document.createElement("div");
    actions.className = "message-actions";
    const extract = addText(actions, "button", "secondary-button", "Extract claims");
    extract.type = "button";
    const status = addText(actions, "span", "extraction-status", "");
    status.setAttribute("role", "status");
    extract.addEventListener("click", () => {
      void extractMessageClaims(savedMessageId, projectId, actions, extract, status);
    });
    article.append(actions);
  }
  elements.messageList.append(article);
  return body;
}

async function loadProjects() {
  const result = await api("/v1/projects");
  state.projects = result.items ?? [];
  const previous = state.selectedProjectId;
  elements.projectSelect.replaceChildren(makeOption("", "All projects"));
  for (const project of state.projects) {
    elements.projectSelect.append(makeOption(project.id, project.name));
  }
  if (state.projects.some((project) => project.id === previous)) {
    elements.projectSelect.value = previous;
  } else {
    state.selectedProjectId = "";
    elements.projectSelect.value = "";
  }
}

async function loadConversations() {
  const requestSequence = ++state.conversationsRequestSequence;
  const projectId = state.selectedProjectId;
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  const result = await api(`/v1/conversations${query}`);
  if (requestSequence !== state.conversationsRequestSequence || projectId !== state.selectedProjectId) return;
  state.conversations = result.items ?? [];
  renderConversations();
}

function renderConversations() {
  elements.conversationList.replaceChildren();
  for (const conversation of state.conversations) {
    const group = document.createElement("div");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "conversation-item";
    button.textContent = conversation.title;
    button.setAttribute("aria-current", String(conversation.id === state.selectedConversationId));
    button.addEventListener("click", () => selectConversation(conversation.id));
    group.append(button);

    if (conversation.id === state.selectedConversationId && state.branches) {
      const branches = document.createElement("div");
      branches.className = "branch-list";
      for (const branch of state.branches) {
        const branchButton = document.createElement("button");
        branchButton.type = "button";
        branchButton.className = "branch-item";
        branchButton.textContent = branch.name;
        branchButton.setAttribute("aria-current", String(branch.id === state.selectedBranchId));
        branchButton.addEventListener("click", () => selectBranch(branch.id));
        branches.append(branchButton);
      }
      group.append(branches);
    }
    elements.conversationList.append(group);
  }
}

async function loadBranches(conversationId) {
  const result = await api(`/v1/conversations/${encodeURIComponent(conversationId)}/branches`);
  return result.items ?? [];
}

async function loadMessages(
  branchId = state.selectedBranchId,
  selectionSequence = state.selectionSequence,
  { preserveScroll = false } = {},
) {
  if (!branchId) return;
  const result = await api(`/v1/branches/${encodeURIComponent(branchId)}/messages`);
  if (selectionSequence !== state.selectionSequence || branchId !== state.selectedBranchId) return;
  const scrollTop = elements.messageList.scrollTop;
  const followLatest = !preserveScroll || isChatNearBottom();
  elements.messageList.replaceChildren();
  for (const message of result.items ?? []) {
    appendMessage(message.role, message.content, message.participant, message.id);
  }
  if (followLatest) scrollChatToBottom();
  else elements.messageList.scrollTop = scrollTop;
}

async function selectConversation(conversationId) {
  chatImages.reset();
  const selectionSequence = ++state.selectionSequence;
  state.contextRequestSequence += 1;
  state.memoryRequestSequence += 1;
  state.selectedConversationId = conversationId;
  state.lastRunId = null;
  const conversation = state.conversations.find((item) => item.id === conversationId);
  state.selectedBranchId = conversation?.root_branch_id ?? null;
  const branches = await loadBranches(conversationId);
  if (selectionSequence !== state.selectionSequence) return;
  state.branches = branches;
  if (branches.length && !branches.some((branch) => branch.id === state.selectedBranchId)) {
    state.selectedBranchId = branches[0].id;
  }
  elements.activeTitle.textContent = conversation?.title ?? "Conversation";
  switchView("chat");
  await loadMessages(state.selectedBranchId, selectionSequence);
  if (selectionSequence !== state.selectionSequence) return;
  renderConversations();
}

async function selectBranch(branchId) {
  if (branchId !== state.selectedBranchId) chatImages.reset();
  const selectionSequence = ++state.selectionSequence;
  state.contextRequestSequence += 1;
  state.memoryRequestSequence += 1;
  state.selectedBranchId = branchId;
  state.lastRunId = null;
  await loadMessages(branchId, selectionSequence);
  if (selectionSequence !== state.selectionSequence) return;
  renderConversations();
  if (state.currentView === "context") void loadContext().catch(showPanelError);
  if (state.currentView === "memory") void loadMemory().catch(showPanelError);
}

async function loadProviders() {
  const result = await api("/v1/providers");
  state.providers = result.items ?? [];
  const localProviders = state.providers.filter((provider) => !provider.is_remote);
  const preferred = localProviders.find((provider) => provider.id === "ollama") ?? localProviders[0];
  elements.providerSelect.replaceChildren();
  if (!preferred) {
    const placeholder = makeOption("", "Choose a provider");
    placeholder.disabled = true;
    elements.providerSelect.append(placeholder);
  }
  for (const provider of state.providers) {
    const label = provider.is_remote && !provider.label.endsWith(" (remote)")
      ? `${provider.label} (remote)`
      : provider.label;
    elements.providerSelect.append(makeOption(provider.id, label));
  }
  elements.providerSelect.value = preferred?.id ?? "";
  if (preferred) {
    await selectProvider(preferred.id);
  }
}

const ollamaControls = $("#ollama-controls");
const startOllamaButton = $("#start-ollama");
const loadOllamaButton = $("#load-ollama-model");
const ollamaStatus = $("#ollama-status");
const openrouterStatus = $("#openrouter-status");
let providerRequestSequence = 0;

function updateModelOptions(select, models) {
  const previous = select.value;
  select.replaceChildren(...models.map((model) => makeOption(model, model)));
  if (models.includes(previous)) select.value = previous;
}

function selectedModel() {
  if (state.selectedProviderId === "ollama") return elements.ollamaModel.value;
  if (state.selectedProviderId === "openrouter_free") {
    return elements.openrouterModel.disabled ? "" : elements.openrouterModel.value;
  }
  return elements.modelName.value.trim();
}

async function selectProvider(providerId) {
  const requestSequence = ++providerRequestSequence;
  state.selectedProviderId = providerId;
  chatImages.updateProvider();
  const isOllama = providerId === "ollama";
  const isOpenRouter = providerId === "openrouter_free";
  elements.modelName.hidden = isOllama || isOpenRouter;
  elements.ollamaModel.hidden = !isOllama;
  elements.openrouterModel.hidden = !isOpenRouter;
  ollamaControls.hidden = !isOllama;
  openrouterStatus.hidden = !isOpenRouter;
  if (isOpenRouter) {
    elements.openrouterModel.disabled = true;
    openrouterStatus.textContent = "Checking free models…";
  }
  if (isOllama) {
    startOllamaButton.hidden = true;
    loadOllamaButton.hidden = true;
    ollamaStatus.textContent = "Checking Ollama…";
  }

  try {
    if (isOpenRouter) {
      const hasKey = await window.cog.hasProviderApiKey(providerId);
      if (requestSequence !== providerRequestSequence) return;
      if (!hasKey) {
        elements.openrouterModel.replaceChildren();
        openrouterStatus.textContent = "Add your OpenRouter key in Settings.";
        return;
      }
    }
    const result = await api(`/v1/providers/${encodeURIComponent(providerId)}/models`, { providerId });
    if (requestSequence !== providerRequestSequence) return;
    const models = result.items ?? [];
    if (isOpenRouter) {
      updateModelOptions(elements.openrouterModel, models);
      elements.openrouterModel.disabled = false;
      openrouterStatus.textContent = "";
      return;
    }
    if (isOllama) {
      updateModelOptions(elements.ollamaModel, models);
      loadOllamaButton.hidden = models.length === 0;
      ollamaStatus.textContent = models.length ? "" : "No installed models found.";
      return;
    }
    if (models.length) {
      const current = elements.modelName.value.trim();
      if (!current || !models.includes(current)) elements.modelName.value = models[0];
      elements.modelName.setAttribute("list", "model-options");
      let datalist = $("#model-options");
      if (!datalist) {
        datalist = document.createElement("datalist");
        datalist.id = "model-options";
        elements.modelName.after(datalist);
      }
      datalist.replaceChildren(...models.map((model) => makeOption(model, model)));
    }
  } catch (error) {
    if (requestSequence !== providerRequestSequence) return;
    if (isOllama) {
      elements.ollamaModel.replaceChildren();
      startOllamaButton.hidden = false;
      ollamaStatus.textContent = "Ollama unavailable.";
    } else if (isOpenRouter) {
      elements.openrouterModel.replaceChildren();
      openrouterStatus.textContent = `OpenRouter unavailable: ${error.message}`;
    } else {
      elements.chatStatus.textContent = `Model discovery unavailable: ${error.message}`;
    }
  }
}

startOllamaButton.addEventListener("click", async () => {
  startOllamaButton.disabled = true;
  ollamaStatus.textContent = "Connecting to Ollama…";
  try {
    await window.cog.startOllama();
    if (state.selectedProviderId === "ollama") await selectProvider("ollama");
  } catch (error) {
    ollamaStatus.textContent = error.message.replace(/^Error invoking remote method '[^']+': Error: /, "");
  } finally {
    startOllamaButton.disabled = false;
  }
});

loadOllamaButton.addEventListener("click", async () => {
  const model = elements.ollamaModel.value;
  if (!model) return;
  loadOllamaButton.disabled = true;
  ollamaStatus.textContent = `Loading ${model}…`;
  try {
    await window.cog.loadOllamaModel(model);
    ollamaStatus.textContent = `${model} loaded.`;
  } catch (error) {
    ollamaStatus.textContent = error.message.replace(/^Error invoking remote method '[^']+': Error: /, "");
  } finally {
    loadOllamaButton.disabled = false;
  }
});

async function requestText(label) {
  return requestInput(label);
}

async function requestChoice(label, options, defaultValue) {
  return requestInput(label, options, defaultValue);
}

function requestInput(label, options, defaultValue = "") {
  const dialog = $("#input-dialog");
  const text = $("#input-dialog-value");
  const choice = $("#input-dialog-choice");
  const input = options ? choice : text;
  text.hidden = input !== text;
  choice.hidden = input !== choice;
  const inputLabel = $("#input-dialog-label");
  inputLabel.htmlFor = input.id;
  inputLabel.textContent = label;
  if (options) choice.replaceChildren(...options.map(([value, name]) => makeOption(value, name)));
  $("#input-dialog-heading").textContent = label;
  input.value = defaultValue;
  dialog.returnValue = "";

  return new Promise((resolve) => {
    dialog.addEventListener("close", () => {
      resolve(dialog.returnValue === "submit" ? input.value : null);
    }, { once: true });
    dialog.showModal();
    input.focus();
    if (input === text) text.select();
  });
}

async function createProject() {
  const name = await requestText("Project name");
  if (!name?.trim()) return;
  const created = await api("/v1/projects", {
    method: "POST",
    body: { name: name.trim(), description: null },
  });
  chatImages.reset();
  state.selectedConversationId = null;
  state.selectedBranchId = null;
  state.branches = [];
  elements.activeTitle.textContent = "Choose a conversation";
  elements.chatPanel.hidden = true;
  elements.emptyState.hidden = state.currentView !== "chat";
  await loadProjects();
  state.selectedProjectId = created.id;
  elements.projectSelect.value = created.id;
  await loadConversations();
}

async function createConversation() {
  const title = await requestText("Conversation name");
  if (!title?.trim()) return;
  const conversation = await api("/v1/conversations", {
    method: "POST",
    body: { title: title.trim(), project_id: state.selectedProjectId || null },
  });
  await loadConversations();
  await selectConversation(conversation.id);
}

async function sendMessage(event) {
  event.preventDefault();
  const provider = state.providers.find((item) => item.id === state.selectedProviderId);
  if (!state.selectedBranchId || !provider || elements.sendButton.disabled) return;
  if (chatImages.loading) {
    elements.chatStatus.textContent = "Wait for the images to finish loading.";
    return;
  }
  const images = chatImages.payload();
  let content = elements.messageInput.value.trim();
  if (!content) {
    if (!images.length) return;
    content = images.length === 1 ? "Describe the attached image." : "Describe the attached images.";
  }

  const model = selectedModel();
  if (!model) {
    elements.chatStatus.textContent = "Enter a model name before sending.";
    return;
  }

  const branchId = state.selectedBranchId;
  elements.messageInput.value = "";
  chatImages.reset();
  appendMessage("user", content, "You");
  const assistantBody = appendMessage("assistant", "", "Assistant");
  scrollChatToBottom();
  elements.sendButton.disabled = true;
  elements.chatStatus.textContent = "Generating…";

  state.cancelStream = window.cog.stream(
    `/v1/branches/${encodeURIComponent(branchId)}/chat`,
    {
      method: "POST",
      providerId: provider.id,
      body: {
        content,
        provider: provider.id,
        model,
        allow_remote: Boolean(provider.is_remote),
        ...(images.length ? { images } : {}),
      },
    },
    async (eventName, data) => {
      if (eventName === "token") {
        const followLatest = elements.messageList.contains(assistantBody) && isChatNearBottom();
        assistantBody.textContent += data.token ?? "";
        if (followLatest) scrollChatToBottom();
      } else if (eventName === "done") {
        if (state.selectedBranchId === branchId) state.lastRunId = data.run_id ?? state.lastRunId;
        elements.chatStatus.textContent = "Response complete.";
        state.cancelStream = null;
        elements.sendButton.disabled = false;
        if (state.selectedBranchId === branchId) {
          await loadMessages(branchId, state.selectionSequence, { preserveScroll: true });
          if (state.currentView === "context") await loadContext();
        }
      } else if (eventName === "error") {
        const message = data?.message ?? data?.data?.error?.message ?? "The provider request failed.";
        elements.chatStatus.textContent = message;
        state.cancelStream = null;
        elements.sendButton.disabled = false;
      }
    },
  );
}


const views = {
  chat: $("#chat-panel"),
  context: $("#context-panel"),
  memory: $("#memory-panel"),
  claims: $("#claims-panel"),
  settings: $("#settings-panel"),
};
function switchView(name) {
  if (!views[name]) return;
  if (state.currentView === "context" && name !== "context") state.contextRequestSequence += 1;
  if (state.currentView === "memory" && name !== "memory") state.memoryRequestSequence += 1;
  state.currentView = name;
  document.querySelectorAll(".view-tab").forEach((button) => {
    button.setAttribute("aria-current", String(button.dataset.view === name));
  });
  for (const [key, panel] of Object.entries(views)) {
    panel.hidden = key !== name || (key === "chat" && !state.selectedConversationId);
  }
  elements.emptyState.hidden = name !== "chat" || Boolean(state.selectedConversationId);
  if (name === "context") void loadContext().catch(showPanelError);
  if (name === "memory") void loadMemory().catch(showPanelError);
  if (name === "claims") void loadClaims().catch(showPanelError);
  if (name === "settings") void loadSettings().catch(showPanelError);
}
function showPanelError(error) {
  const message = error?.message ?? String(error);
  const panel = views[state.currentView];
  if (!panel || state.currentView === "chat") {
    elements.chatStatus.textContent = message;
    return;
  }
  panel.querySelectorAll(".panel-error").forEach((node) => node.remove());
  const notice = document.createElement("p");
  notice.className = "panel-error";
  notice.textContent = message;
  panel.prepend(notice);
}
function addText(parent, tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value ?? "";
  parent.append(node);
  return node;
}
function recordCard(parent, title, subtitle, body) {
  const card = document.createElement("article");
  card.className = "record-card";
  addText(card, "h3", "", title);
  if (subtitle) addText(card, "div", "record-meta", subtitle);
  if (body) addText(card, "p", "record-body", body);
  parent.append(card);
  return card;
}
async function loadContext() {
  const requestSequence = ++state.contextRequestSequence;
  const branchId = state.selectedBranchId;
  const target = $("#context-content");
  target.replaceChildren();
  if (!branchId) {
    addText(target, "p", "muted", "Choose a conversation to inspect its latest context packet.");
    return;
  }
  addText(target, "p", "muted", "Loading the latest saved context packet…");
  let latest;
  try {
    latest = await api(`/v1/branches/${encodeURIComponent(branchId)}/runs/latest`);
  } catch (error) {
    if (requestSequence !== state.contextRequestSequence || state.currentView !== "context" || branchId !== state.selectedBranchId) return;
    throw error;
  }
  if (requestSequence !== state.contextRequestSequence || state.currentView !== "context" || branchId !== state.selectedBranchId) return;
  const runId = latest.run?.id ?? null;
  state.lastRunId = runId;
  target.replaceChildren();
  if (!runId) {
    addText(target, "p", "muted", "No saved context packet exists for this branch yet. Send a message first.");
    return;
  }
  addText(target, "p", "muted", "Loading the saved packet…");
  let snapshot;
  let run;
  try {
    [snapshot, run] = await Promise.all([
      api(`/v1/runs/${encodeURIComponent(runId)}/context`),
      api(`/v1/runs/${encodeURIComponent(runId)}`),
    ]);
  } catch (error) {
    if (requestSequence !== state.contextRequestSequence || state.currentView !== "context" || branchId !== state.selectedBranchId || runId !== state.lastRunId) return;
    throw error;
  }
  if (requestSequence !== state.contextRequestSequence || state.currentView !== "context" || branchId !== state.selectedBranchId || runId !== state.lastRunId) return;
  target.replaceChildren();
  const packet = snapshot.packet ?? {};
  recordCard(target, "Run", `${run.status ?? "unknown"} · ${run.id}`, `Provider: ${snapshot.provider_label} · Estimated text tokens: ${snapshot.token_estimate}`);
  const messages = Array.isArray(packet.messages) ? packet.messages : [];
  const imageCount = packet.image_count ? ` · ${packet.image_count} ${packet.image_count === 1 ? "image" : "images"}` : "";
  recordCard(target, "Packet", `${messages.length} messages${imageCount}`, "Message text and attachment count from the context packet.");
  for (const message of messages) recordCard(target, String(message.role ?? "message"), message.participant ?? "", message.content ?? "");
  const dropped = packet.excluded_sources ?? [];
  recordCard(target, "Included sources", `${(packet.included_sources ?? []).length} references`, JSON.stringify(packet.included_sources ?? [], null, 2));
  recordCard(target, "Compiler metadata", "", JSON.stringify({compiler_version:packet.compiler_version, section_allocations:packet.section_allocations, transformations:packet.transformations, max_input_tokens:packet.max_input_tokens, reserve_output_tokens:packet.reserve_output_tokens, input_budget:packet.input_budget}, null, 2));
  if (Array.isArray(dropped) && dropped.length) recordCard(target, "Dropped context", `${dropped.length} omitted items`, JSON.stringify(dropped, null, 2));
}
async function loadMemory() {
  const requestSequence = ++state.memoryRequestSequence;
  const target = $("#memory-content");
  target.replaceChildren();
  addText(target, "p", "muted", "Loading visible memory…");
  const params = new URLSearchParams({state: $("#memory-state").value, limit: "100"});
  if ($("#memory-scope").value) params.set("scope", $("#memory-scope").value);
  if (state.selectedProjectId) params.set("project_id", state.selectedProjectId);
  if (state.selectedConversationId) params.set("conversation_id", state.selectedConversationId);
  if (state.selectedBranchId) params.set("branch_id", state.selectedBranchId);
  let result;
  try {
    result = await api(`/v1/memory?${params}`);
  } catch (error) {
    if (requestSequence !== state.memoryRequestSequence || state.currentView !== "memory") return;
    throw error;
  }
  if (requestSequence !== state.memoryRequestSequence || state.currentView !== "memory") return;
  target.replaceChildren();
  for (const item of result.items ?? []) {
    const card = recordCard(target, item.content, `${item.kind} · ${item.scope}${item.scope_id ? " · " + item.scope_id : ""} · importance ${item.importance} · ${item.state}`, `Origin: ${item.origin_kind}${item.origin_ref ? " · " + item.origin_ref : ""}`);
    if (item.state === "active") {
      const outdated = document.createElement("button");
      outdated.type = "button"; outdated.className = "secondary-button"; outdated.textContent = "Mark outdated";
      outdated.addEventListener("click", async () => {
        await api(`/v1/memory/${encodeURIComponent(item.id)}`, {method:"PATCH",body:{schema_version:1,state:"outdated"}});
        await loadMemory();
      });
      card.append(outdated);
    }
  }
  if (!(result.items ?? []).length) addText(target, "p", "muted", "No active memory matches these filters. Try All states or broaden the selected scope.");
}
async function createMemory() {
  const content = await requestText("Memory content");
  if (!content?.trim()) return;
  const scope = $("#memory-scope").value || (state.selectedProjectId ? "project" : "user");
  const kind = await requestChoice("Memory kind", [
    ["preference", "Preference"],
    ["fact", "Fact"],
    ["decision", "Decision"],
    ["goal", "Goal"],
    ["procedure", "Procedure"],
    ["open_question", "Open question"],
    ["pattern", "Pattern"],
  ], "fact");
  if (!kind) return;
  const scopeId = scope === "project" ? state.selectedProjectId : scope === "conversation" ? state.selectedConversationId : scope === "branch" ? state.selectedBranchId : null;
  if (["project","conversation","branch"].includes(scope) && !scopeId) {
    throw new Error(`Select a ${scope} before creating memory in that scope.`);
  }
  await api("/v1/memory", {method:"POST",body:{schema_version:1,scope,scope_id:scopeId,kind,content:content.trim(),importance:3,origin_kind:"user"}});
  await loadMemory();
}
const claimDialog = $("#claim-dialog");
const claimForm = $("#claim-form");
const claimFormError = $("#claim-form-error");
const saveClaimButton = $("#save-claim");

function openClaimForm() {
  claimForm.reset();
  claimForm.querySelector("details").open = false;
  claimFormError.hidden = true;
  claimForm.dataset.projectId = state.selectedProjectId || "";
  $("#claim-scope").textContent = state.selectedProjectId
    ? elements.projectSelect.selectedOptions[0].textContent
    : "Global scope";
  claimDialog.showModal();
}

async function createClaim(event) {
  event.preventDefault();
  if (saveClaimButton.disabled) return;
  const fields = new FormData(claimForm);
  const text = fields.get("text").trim();
  claimFormError.hidden = true;
  if (!text) {
    claimFormError.textContent = "Enter claim text.";
    claimFormError.hidden = false;
    $("#claim-text").focus();
    return;
  }

  const body = {
    project_id: claimForm.dataset.projectId || null,
    claim_type: fields.get("claim_type"),
    text,
    subject: fields.get("subject").trim() || null,
    predicate: fields.get("predicate").trim() || null,
    object: fields.get("object").trim() || null,
    valid_from: fields.get("valid_from") || null,
    valid_to: fields.get("valid_to") || null,
  };
  if (body.valid_from && body.valid_to && body.valid_to < body.valid_from) {
    claimFormError.textContent = "Valid to must be on or after Valid from.";
    claimFormError.hidden = false;
    return;
  }

  let claim;
  saveClaimButton.disabled = true;
  $("#cancel-claim").disabled = true;
  try {
    claim = await api("/v1/claims", { method: "POST", body });
  } catch (error) {
    claimFormError.textContent = error.message;
    claimFormError.hidden = false;
    return;
  } finally {
    saveClaimButton.disabled = false;
    $("#cancel-claim").disabled = false;
  }

  claimDialog.close();
  $("#claim-search").value = "";
  await loadClaims();
  await showClaim(claim.id);
}

async function loadClaims() {
  const target = $("#claims-list");
  target.replaceChildren();
  const params = new URLSearchParams({limit:"100"});
  if (state.selectedProjectId) params.set("project_id", state.selectedProjectId);
  const query = $("#claim-search").value.trim();
  if (query) params.set("q", query);
  const result = await api(`/v1/claims?${params}`);
  state.claims = result.items ?? [];
  for (const claim of state.claims) {
    const button = document.createElement("button");
    button.type = "button"; button.className = "claim-item";
    button.textContent = claim.text;
    button.setAttribute("aria-current", "false");
    button.addEventListener("click", () => showClaim(claim.id));
    target.append(button);
  }
  if (!state.claims.length) addText(target, "p", "muted", "No claims found for this project.");
  await loadOpenQuestions();
}
function editClaimRecord(dialog, save) {
  const form = dialog.querySelector("form");
  const error = dialog.querySelector("[role=alert]");
  const cancel = form.querySelector("[type=button]");
  const submit = form.querySelector("[type=submit]");
  const submitLabel = submit.textContent;
  form.reset();
  error.hidden = true;
  dialog.showModal();

  return new Promise((resolve) => {
    const cancelClick = () => dialog.close();
    const keepOpenWhileSaving = (event) => {
      if (submit.disabled) event.preventDefault();
    };
    const saveRecord = async (event) => {
      event.preventDefault();
      if (submit.disabled) return;
      const fields = new FormData(form);
      error.hidden = true;
      cancel.disabled = true;
      submit.disabled = true;
      form.setAttribute("aria-busy", "true");
      submit.textContent = dialog.id === "extraction-dialog" ? "Extracting…" : "Saving…";
      try {
        const result = await save(fields);
        resolve(result);
        dialog.close();
      } catch (failure) {
        error.textContent = failure.message;
        error.hidden = false;
      } finally {
        cancel.disabled = false;
        submit.disabled = false;
        submit.textContent = submitLabel;
        form.removeAttribute("aria-busy");
      }
    };
    cancel.addEventListener("click", cancelClick);
    dialog.addEventListener("cancel", keepOpenWhileSaving);
    form.addEventListener("submit", saveRecord);
    dialog.addEventListener("close", () => {
      cancel.removeEventListener("click", cancelClick);
      dialog.removeEventListener("cancel", keepOpenWhileSaving);
      form.removeEventListener("submit", saveRecord);
      resolve(null);
    }, { once: true });
  });
}

async function extractMessageClaims(messageId, projectId, actions, button, status) {
  const provider = state.providers.find((item) => item.id === state.selectedProviderId);
  const model = selectedModel();
  if (!provider || !model) {
    status.textContent = "Select a provider and enter a model above.";
    return;
  }

  const isRemote = Boolean(provider.is_remote);
  const optIn = $("#extraction-remote");
  $("#extraction-model").textContent = `${provider.label} · ${model}`;
  $("#extraction-remote-label").hidden = !isRemote;
  optIn.disabled = !isRemote;
  optIn.required = isRemote;
  button.disabled = true;
  try {
    const result = await editClaimRecord($("#extraction-dialog"), async (fields) => {
      try {
        return await api(`/v1/messages/${encodeURIComponent(messageId)}/extract-claims`, {
          method: "POST",
          providerId: provider.id,
          body: {
            provider: provider.id,
            model,
            allow_remote: isRemote && fields.has("allow_remote"),
          },
        });
      } catch (error) {
        status.textContent = error.message;
        return null;
      }
    });
    if (!result) return;

    const count = result.claim_ids.length;
    status.textContent = count === 0
      ? "The model proposed no claims from this message."
      : count === 1 ? "1 claim proposed." : `${count} claims proposed.`;
    actions.querySelector(".review-extracted-claims")?.remove();
    if (!count) return;

    const review = addText(actions, "button", "secondary-button review-extracted-claims", "Review claims");
    review.type = "button";
    review.addEventListener("click", () => {
      if (elements.projectSelect.value !== projectId) {
        elements.projectSelect.value = projectId;
        elements.projectSelect.dispatchEvent(new Event("change"));
      }
      $("#claim-search").value = "";
      switchView("claims");
      void showClaim(result.claim_ids[0]).catch(showPanelError);
    });
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function attachClaimEvidence(claim, projectId, preferredSourceId) {
  const pageSize = 100;
  const params = new URLSearchParams({ limit: String(pageSize) });
  if (projectId) params.set("project_id", projectId);
  const select = $("#evidence-source");
  const options = document.createDocumentFragment();
  for (let offset = 0; ; offset += pageSize) {
    params.set("offset", String(offset));
    const { items } = await api(`/v1/sources?${params}`);
    for (const source of items) {
      const name = source.title || source.uri || source.id;
      const option = makeOption(source.id, `${name} (${source.kind})`);
      option.defaultSelected = source.id === preferredSourceId;
      options.append(option);
    }
    if (items.length < pageSize) break;
  }
  if (!options.childNodes.length) {
    showPanelError(new Error("Register a source before attaching evidence."));
    return;
  }

  select.replaceChildren(options);
  const scope = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  const result = await editClaimRecord($("#evidence-dialog"), (fields) => api(
    `/v1/claims/${encodeURIComponent(claim.id)}/evidence${scope}`, {
      method: "POST",
      body: {
        source_id: fields.get("source_id"),
        stance: fields.get("stance"),
        excerpt: fields.get("excerpt") || null,
        locator: fields.get("locator").trim() || null,
      },
    },
  ));
  if (result && state.currentView === "claims" && (state.selectedProjectId || null) === projectId) {
    await showClaim(claim.id);
  }
}

async function registerClaimSource(claim, projectId) {
  const source = await editClaimRecord($("#source-dialog"), (fields) => api("/v1/sources", {
    method: "POST",
    body: {
      project_id: claim.project_id,
      kind: fields.get("kind"),
      title: fields.get("title").trim() || null,
      uri: fields.get("uri").trim() || null,
    },
  }));
  if (source) await attachClaimEvidence(claim, projectId, source.id);
}

async function addClaimAssessment(claimId, projectId) {
  const scope = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  const result = await editClaimRecord($("#assessment-dialog"), (fields) => {
    const score = fields.get("value_num");
    const text = fields.get("value_text").trim();
    if ((score !== "") === Boolean(text)) {
      throw new Error("Enter either a score or a written assessment.");
    }
    return api(`/v1/claims/${encodeURIComponent(claimId)}/assessments${scope}`, {
      method: "POST",
      body: {
        dimension: fields.get("dimension"),
        value_num: score === "" ? null : Number(score),
        value_text: text || null,
        rationale: fields.get("rationale").trim() || null,
      },
    });
  });
  if (result && state.currentView === "claims" && (state.selectedProjectId || null) === projectId) {
    await showClaim(claimId);
  }
}

const relationshipType = $("#relationship-type");
const contradictionBasis = $("#contradiction-basis");

function updateContradictionBasis() {
  const required = relationshipType.value === "contradicts";
  contradictionBasis.labels[0].hidden = !required;
  contradictionBasis.hidden = !required;
  contradictionBasis.disabled = !required;
  contradictionBasis.required = required;
}

relationshipType.addEventListener("change", updateContradictionBasis);

async function addClaimRelationship(claim, projectId) {
  const options = (await loadClaimOptions(projectId)).filter(([id]) => id !== claim.id);
  if (state.currentView !== "claims" || (state.selectedProjectId || null) !== projectId) return;
  if (!options.length) throw new Error("Create another visible claim before adding a relationship.");

  const target = $("#relationship-target");
  target.replaceChildren(makeOption("", "Choose a claim"));
  for (const [id, text] of options) target.append(makeOption(id, text));
  $("#relationship-claim").textContent = claim.text;
  const scope = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";

  const pending = editClaimRecord($("#relationship-dialog"), (fields) => api(
    `/v1/claims/${encodeURIComponent(claim.id)}/relations${scope}`, {
      method: "POST",
      body: {
        to_claim_id: fields.get("to_claim_id"),
        rel: fields.get("rel"),
        contradiction_basis: fields.get("contradiction_basis"),
        note: fields.get("note").trim() || null,
      },
    },
  ));
  updateContradictionBasis();
  if (await pending) await showClaim(claim.id);
}

async function showClaim(claimId) {
  const projectId = state.selectedProjectId || null;
  const claim = await api(`/v1/claims/${encodeURIComponent(claimId)}${state.selectedProjectId ? "?project_id="+encodeURIComponent(state.selectedProjectId) : ""}`);
  const target = $("#claim-detail"); target.replaceChildren();
  addText(target,"h3","",claim.text);
  addText(target,"div","record-meta",`${claim.claim_type} · ${claim.project_id ? "project scoped" : "global"} · ${claim.origin_kind}`);
  const statuses = claim.current_status ?? [];
  recordCard(target,"Current status",statuses.map(x=>x.scope+": "+x.status).join(" · ") || "No status events","Status is scoped; this view does not infer truth.");
  const evidence = claim.evidence ?? [];
  const evidenceSection = recordCard(target,"Evidence",`${evidence.length} records`,"Sources linked to this claim.");
  for (const item of evidence) {
    const source = item.source_title || item.source_uri || item.source_id;
    const record = recordCard(evidenceSection, source, `${item.stance} · ${item.source_kind}`, item.excerpt);
    if (item.locator) addText(record, "p", "record-meta", item.locator);
  }
  const evidenceActions = document.createElement("div");
  evidenceActions.className = "settings-actions";
  for (const [label, action] of [
    ["Register source", () => registerClaimSource(claim, projectId)],
    ["Attach evidence", () => attachClaimEvidence(claim, projectId)],
  ]) {
    const button = addText(evidenceActions, "button", "secondary-button", label);
    button.type = "button";
    button.addEventListener("click", async () => {
      for (const control of evidenceActions.children) control.disabled = true;
      try {
        await action();
      } catch (error) {
        showPanelError(error);
      } finally {
        for (const control of evidenceActions.children) control.disabled = false;
      }
    });
  }
  evidenceSection.append(evidenceActions);
  const relations = claim.relations ?? [];
  const relationSection = recordCard(target,"Relationships",`${relations.length} links`,"Contradictions are compared side by side; other links remain listed by type.");
  for (const rel of relations) {
    const otherId = rel.from_claim_id === claim.id ? rel.to_claim_id : rel.from_claim_id;
    const otherText = rel.related_claim_text ?? otherId;
    if (rel.rel === "contradicts") {
      const comparison = document.createElement("div");
      comparison.className = "contradiction-pair";
      recordCard(comparison, "Selected claim", "", claim.text);
      recordCard(comparison, "Contradicting claim", rel.contradiction_basis?.replaceAll("_", " "), otherText);
      relationSection.append(comparison);
    } else {
      const direction = rel.from_claim_id === claim.id ? "Outgoing" : "Incoming";
      recordCard(relationSection, otherText, `${direction} · ${rel.rel.replaceAll("_", " ")}`);
    }
    if (rel.note) addText(relationSection, "p", "record-body", rel.note);
  }
  const relationButton = addText(relationSection, "button", "secondary-button", "Add relationship");
  relationButton.type = "button";
  relationButton.addEventListener("click", async () => {
    relationButton.disabled = true;
    try {
      await addClaimRelationship(claim, projectId);
    } catch (error) {
      showPanelError(error);
    } finally {
      relationButton.disabled = false;
    }
  });
  const assessments = claim.assessments ?? [];
  const assessmentSection = recordCard(target,"Assessments",`${assessments.length} records`,"Assessments are recorded independently of status.");
  for (const item of assessments) {
    const dimension = item.dimension.replaceAll("_", " ");
    const value = [item.value_num, item.value_text].filter((part) => part != null).join(" · ");
    recordCard(assessmentSection, dimension, value, item.rationale);
  }
  const assessmentButton = addText(assessmentSection, "button", "secondary-button", "Add assessment");
  assessmentButton.type = "button";
  assessmentButton.addEventListener("click", () => {
    void addClaimAssessment(claim.id, projectId).catch(showPanelError);
  });
  const statusButton=document.createElement("button"); statusButton.type="button"; statusButton.className="secondary-button"; statusButton.textContent="Record status";
  statusButton.addEventListener("click",async()=>{
    const status = await requestChoice("Claim status", [
      ["proposed", "Proposed"],
      ["reported", "Reported"],
      ["inferred", "Inferred"],
      ["corroborated", "Corroborated"],
      ["contested", "Contested"],
      ["accepted", "Accepted"],
      ["rejected", "Rejected"],
      ["superseded", "Superseded"],
      ["unresolved", "Unresolved"],
      ["unknown", "Unknown"],
    ], "reported");
    if(!status)return;
    const payload={schema_version:1,status,scope:"default",rationale:"Recorded from desktop claims panel.",actor_kind:"user"};
    if(status==="accepted") {
      const policy=await requestText("Acceptance policy (required)");
      if(!policy?.trim()) return;
      payload.policy=policy.trim();
    }
    await api(`/v1/claims/${encodeURIComponent(claim.id)}/status${state.selectedProjectId ? "?project_id="+encodeURIComponent(state.selectedProjectId) : ""}`,{method:"POST",body:payload});
    await showClaim(claim.id);
  });
  target.append(statusButton);
}
async function loadClaimOptions(projectId) {
  const claimOptions = [];
  const pageSize = 100;
  const params = new URLSearchParams({ limit: String(pageSize) });
  if (projectId) params.set("project_id", projectId);
  for (let offset = 0; ; offset += pageSize) {
    params.set("offset", String(offset));
    const { items } = await api(`/v1/claims?${params}`);
    for (const claim of items) claimOptions.push([claim.id, claim.text]);
    if (items.length < pageSize) break;
  }

  return claimOptions;
}

async function createOpenQuestion() {
  const text=await requestText("What question remains unresolved?");
  if(!text?.trim()) return;
  const projectId = state.selectedProjectId || null;
  const claimOptions = await loadClaimOptions(projectId);
  const related = claimOptions.length
    ? await requestChoice("Related claim (optional)", [["", "No related claim"], ...claimOptions], "")
    : "";
  if (related === null) return;
  await api("/v1/open-questions", {
    method: "POST",
    body: { schema_version: 1, project_id: projectId, text: text.trim(), related_claim_id: related || null },
  });
  await loadOpenQuestions();
}
async function loadOpenQuestions() {
  const target=$("#open-questions-list"); target.replaceChildren();
  const query=state.selectedProjectId ? "?project_id="+encodeURIComponent(state.selectedProjectId) : "";
  const result=await api("/v1/open-questions"+query);
  for(const item of result.items??[]){
    const card=recordCard(target,item.text,item.state,item.related_claim_id??"");
    if(["open","investigating"].includes(item.state)){
      const select=document.createElement("select");
      for(const value of ["open","investigating","answered","dropped"]) select.append(makeOption(value,value));
      select.value=item.state;
      const save=document.createElement("button"); save.type="button"; save.className="secondary-button"; save.textContent="Update";
      save.addEventListener("click",async()=>{await api(`/v1/open-questions/${encodeURIComponent(item.id)}${state.selectedProjectId ? "?project_id="+encodeURIComponent(state.selectedProjectId) : ""}`,{method:"PATCH",body:{schema_version:1,state:select.value}});await loadOpenQuestions();});
      card.append(select,save);
    }
  }
  if(!(result.items??[]).length) addText(target,"p","muted","No open questions.");
}
document.querySelectorAll(".view-tab").forEach(button=>button.addEventListener("click",()=>switchView(button.dataset.view)));
$("#refresh-context").addEventListener("click",()=>void loadContext().catch(showPanelError));
$("#memory-scope").addEventListener("change",()=>void loadMemory().catch(showPanelError));
$("#memory-state").addEventListener("change",()=>void loadMemory().catch(showPanelError));
$("#new-memory").addEventListener("click",()=>void createMemory().catch(showPanelError));
$("#new-claim").addEventListener("click", openClaimForm);
$("#cancel-claim").addEventListener("click", () => claimDialog.close());
claimDialog.addEventListener("cancel", (event) => {
  if (saveClaimButton.disabled) event.preventDefault();
});
claimForm.addEventListener("submit", (event) => void createClaim(event).catch(showPanelError));
$("#refresh-claims").addEventListener("click",()=>void loadClaims().catch(showPanelError));
$("#new-open-question").addEventListener("click",()=>void createOpenQuestion().catch(showPanelError));
$("#refresh-settings").addEventListener("click",()=>void loadSettings().catch(showPanelError));
$("#key-provider").addEventListener("change",()=>void window.cog.hasProviderApiKey($("#key-provider").value).then(saved=>{$("#provider-key-status").textContent=saved?"A key is saved securely for this provider.":"No key saved for this provider.";}));
$("#save-provider-key").addEventListener("click",()=>void saveProviderKey().catch(showPanelError));
$("#delete-provider-key").addEventListener("click",()=>void deleteProviderKey().catch(showPanelError));
$("#save-sharing-settings").addEventListener("click",()=>void saveSharingSettings().catch(showPanelError));
$("#claim-search").addEventListener("change",()=>void loadClaims().catch(showPanelError));


async function loadSettings() {
  const keySelect=$("#key-provider"); keySelect.replaceChildren();
  for(const provider of state.providers) keySelect.append(makeOption(provider.id,provider.label));
  if(state.selectedProviderId) keySelect.value=state.selectedProviderId;
  $("#data-directory").textContent=await window.cog.getDataDirectory();
  const secureStorage=await window.cog.getSecureStorageStatus();
  $("#secure-storage-status").textContent=secureStorage.secure ? `OS secure storage: ${secureStorage.backend}` : `Secure storage unavailable or insecure: ${secureStorage.backend}. Provider keys cannot be saved.`;
  const saved=keySelect.value ? await window.cog.hasProviderApiKey(keySelect.value) : false;
  $("#provider-key-status").textContent=saved ? "A key is saved securely for this provider." : "No key saved for this provider.";
  const values=await api("/v1/settings");
  $("#share-global-memory").checked=Boolean(values.share_global_memory_remote);
  $("#share-user-memory").checked=Boolean(values.share_user_memory_remote);
}
async function saveProviderKey() {
  const providerId=$("#key-provider").value;
  const value=$("#provider-api-key").value;
  if(!providerId) throw new Error("Choose a provider first.");
  if(!value.trim()) throw new Error("Enter an API key to save.");
  await window.cog.setProviderApiKey(providerId,value);
  $("#provider-api-key").value="";
  $("#provider-key-status").textContent="Key encrypted and saved by the operating system.";
  if (providerId === "openrouter_free" && providerId === state.selectedProviderId) {
    void selectProvider(providerId);
  }
}
async function deleteProviderKey() {
  const providerId=$("#key-provider").value;
  if(!providerId) return;
  await window.cog.deleteProviderApiKey(providerId);
  $("#provider-key-status").textContent="Saved key deleted.";
  if (providerId === "openrouter_free" && providerId === state.selectedProviderId) {
    void selectProvider(providerId);
  }
}
async function saveSharingSettings() {
  await api("/v1/settings",{method:"PATCH",body:{
    share_global_memory_remote:$("#share-global-memory").checked,
    share_user_memory_remote:$("#share-user-memory").checked,
  }});
  $("#provider-key-status").textContent="Remote memory-sharing settings saved.";
}

async function initialize() {
  try {
    const health = await api("/v1/health");
    setConnectionStatus(`Connected · backend ${health.version}`);
    await loadProjects();
    await loadConversations();
    await loadProviders();
  } catch (error) {
    setConnectionStatus(`Backend unavailable · ${error.message}`, "error");
  }
}

elements.projectSelect.addEventListener("change", async () => {
  state.selectionSequence += 1;
  state.contextRequestSequence += 1;
  state.memoryRequestSequence += 1;
  state.lastRunId = null;
  state.selectedProjectId = elements.projectSelect.value;
  chatImages.reset();
  state.selectedConversationId = null;
  state.selectedBranchId = null;
  state.branches = [];
  elements.activeTitle.textContent = "Choose a conversation";
  elements.chatPanel.hidden = true;
  elements.emptyState.hidden = state.currentView !== "chat";
  await loadConversations();
  if (state.currentView === "context") void loadContext().catch(showPanelError);
  if (state.currentView === "memory") void loadMemory().catch(showPanelError);
});

elements.newProject.addEventListener("click", () => void createProject().catch((error) => {
  elements.chatStatus.textContent = error.message;
}));
elements.newConversation.addEventListener("click", () => void createConversation().catch((error) => {
  elements.chatStatus.textContent = error.message;
}));
elements.providerSelect.addEventListener("change", () => void selectProvider(elements.providerSelect.value));
bindChatTools({
  messageInput: elements.messageInput,
  api,
  getSelectionSequence: () => state.selectionSequence,
});
bindExplorerTool({
  messageInput: elements.messageInput,
  getSelectionSequence: () => state.selectionSequence,
});
elements.composer.addEventListener("submit", (event) => void sendMessage(event));
elements.messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.composer.requestSubmit();
  }
});

void initialize();
