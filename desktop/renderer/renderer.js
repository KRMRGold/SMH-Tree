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
  remoteWrap: $("#remote-toggle-wrap"),
  allowRemote: $("#allow-remote"),
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
  selectedProviderRemote: false,
  cancelStream: null,
};

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

function appendMessage(role, content, participant = role) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = participant || role;

  const body = document.createElement("div");
  body.className = "message-content";
  body.textContent = content ?? "";

  article.append(meta, body);
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
  const query = state.selectedProjectId
    ? `?project_id=${encodeURIComponent(state.selectedProjectId)}`
    : "";
  const result = await api(`/v1/conversations${query}`);
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
  state.branches = result.items ?? [];
}

async function loadMessages() {
  if (!state.selectedBranchId) return;
  const result = await api(`/v1/branches/${encodeURIComponent(state.selectedBranchId)}/messages`);
  elements.messageList.replaceChildren();
  for (const message of result.items ?? []) {
    appendMessage(message.role, message.content, message.participant);
  }
  elements.messageList.scrollTop = elements.messageList.scrollHeight;
}

async function selectConversation(conversationId) {
  state.selectedConversationId = conversationId;
  const conversation = state.conversations.find((item) => item.id === conversationId);
  state.selectedBranchId = conversation?.root_branch_id ?? null;
  await loadBranches(conversationId);
  if (state.branches.length && !state.branches.some((branch) => branch.id === state.selectedBranchId)) {
    state.selectedBranchId = state.branches[0].id;
  }
  elements.activeTitle.textContent = conversation?.title ?? "Conversation";
  elements.emptyState.hidden = true;
  elements.chatPanel.hidden = false;
  await loadMessages();
  renderConversations();
}

async function selectBranch(branchId) {
  state.selectedBranchId = branchId;
  await loadMessages();
  renderConversations();
}

async function loadProviders() {
  const result = await api("/v1/providers");
  state.providers = result.items ?? [];
  elements.providerSelect.replaceChildren();
  for (const provider of state.providers) {
    elements.providerSelect.append(makeOption(provider.id, provider.label));
  }
  const preferred = state.providers.find((provider) => provider.id === "ollama") ?? state.providers[0];
  if (preferred) {
    elements.providerSelect.value = preferred.id;
    await selectProvider(preferred.id);
  }
}

async function selectProvider(providerId) {
  state.selectedProviderId = providerId;
  const provider = state.providers.find((item) => item.id === providerId);
  state.selectedProviderRemote = Boolean(provider?.is_remote);
  elements.remoteWrap.hidden = !state.selectedProviderRemote;
  if (!state.selectedProviderRemote) elements.allowRemote.checked = false;

  try {
    const result = await api(`/v1/providers/${encodeURIComponent(providerId)}/models`);
    const models = result.items ?? [];
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
    elements.chatStatus.textContent = `Model discovery unavailable: ${error.message}`;
  }
}

async function createProject() {
  const name = window.prompt("Project name");
  if (!name?.trim()) return;
  const created = await api("/v1/projects", {
    method: "POST",
    body: { name: name.trim(), description: null },
  });
  state.selectedConversationId = null;
  state.selectedBranchId = null;
  state.branches = [];
  elements.activeTitle.textContent = "Choose a conversation";
  elements.chatPanel.hidden = true;
  elements.emptyState.hidden = false;
  await loadProjects();
  state.selectedProjectId = created.id;
  elements.projectSelect.value = created.id;
  await loadConversations();
}

async function createConversation() {
  const title = window.prompt("Conversation name");
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
  const content = elements.messageInput.value.trim();
  if (!content || !state.selectedBranchId || !state.selectedProviderId) return;

  const model = elements.modelName.value.trim();
  if (!model) {
    elements.chatStatus.textContent = "Enter a model name before sending.";
    return;
  }

  const allowRemote = state.selectedProviderRemote && elements.allowRemote.checked;
  elements.allowRemote.checked = false;
  elements.messageInput.value = "";
  appendMessage("user", content, "You");
  const assistantBody = appendMessage("assistant", "", "Assistant");
  elements.sendButton.disabled = true;
  elements.chatStatus.textContent = "Generating…";

  state.cancelStream = window.cog.stream(
    `/v1/branches/${encodeURIComponent(state.selectedBranchId)}/chat`,
    {
      method: "POST",
      body: {
        content,
        provider: state.selectedProviderId,
        model,
        allow_remote: allowRemote,
      },
    },
    async (eventName, data) => {
      if (eventName === "token") {
        assistantBody.textContent += data.token ?? "";
      } else if (eventName === "done") {
        elements.chatStatus.textContent = "Response complete.";
        state.cancelStream = null;
        elements.sendButton.disabled = false;
        await loadMessages();
      } else if (eventName === "error") {
        const message = data?.message ?? data?.data?.error?.message ?? "The provider request failed.";
        elements.chatStatus.textContent = message;
        state.cancelStream = null;
        elements.sendButton.disabled = false;
      }
    },
  );
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
  state.selectedProjectId = elements.projectSelect.value;
  state.selectedConversationId = null;
  state.selectedBranchId = null;
  state.branches = [];
  elements.activeTitle.textContent = "Choose a conversation";
  elements.chatPanel.hidden = true;
  elements.emptyState.hidden = false;
  await loadConversations();
});

elements.newProject.addEventListener("click", () => void createProject().catch((error) => {
  elements.chatStatus.textContent = error.message;
}));
elements.newConversation.addEventListener("click", () => void createConversation().catch((error) => {
  elements.chatStatus.textContent = error.message;
}));
elements.providerSelect.addEventListener("change", () => void selectProvider(elements.providerSelect.value));
elements.composer.addEventListener("submit", (event) => void sendMessage(event));
elements.messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.composer.requestSubmit();
  }
});

void initialize();
