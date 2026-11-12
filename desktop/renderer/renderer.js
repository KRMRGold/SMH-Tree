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
  lastRunId: null,
  currentView: "chat",
  claims: [],
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
  switchView("chat");
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
    const result = await api(`/v1/providers/${encodeURIComponent(providerId)}/models`, { providerId });
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
      providerId: state.selectedProviderId,
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
        state.lastRunId = data.run_id ?? state.lastRunId;
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


const views = {
  chat: $("#chat-panel"),
  context: $("#context-panel"),
  memory: $("#memory-panel"),
  claims: $("#claims-panel"),
  settings: $("#settings-panel"),
};
function switchView(name) {
  if (!views[name]) return;
  state.currentView = name;
  document.querySelectorAll(".view-tab").forEach((button) => {
    button.setAttribute("aria-current", String(button.dataset.view === name));
  });
  for (const [key, panel] of Object.entries(views)) panel.hidden = key !== name;
  if (name === "context") void loadContext().catch(showPanelError);
  if (name === "memory") void loadMemory().catch(showPanelError);
  if (name === "claims") void loadClaims().catch(showPanelError);
  if (name === "settings") void loadSettings().catch(showPanelError);
}
function showPanelError(error) {
  elements.chatStatus.textContent = error?.message ?? String(error);
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
  const target = $("#context-content");
  target.replaceChildren();
  if (!state.lastRunId) {
    addText(target, "p", "muted", "No run in this session yet. Send a message first.");
    return;
  }
  const [snapshot, run] = await Promise.all([
    api(`/v1/runs/${encodeURIComponent(state.lastRunId)}/context`),
    api(`/v1/runs/${encodeURIComponent(state.lastRunId)}`),
  ]);
  recordCard(target, "Run", `${run.status ?? "unknown"} · ${run.id}`, `Provider: ${snapshot.provider_label} · Estimated tokens: ${snapshot.token_estimate}`);
  const packet = snapshot.packet ?? {};
  const messages = Array.isArray(packet.messages) ? packet.messages : [];
  recordCard(target, "Packet", `${messages.length} messages`, "Exact stored packet sent to the provider. Sensitive content is displayed locally.");
  for (const message of messages) recordCard(target, String(message.role ?? "message"), message.participant ?? "", message.content ?? "");
  const dropped = packet.excluded_sources ?? [];
  recordCard(target, "Included sources", `${(packet.included_sources ?? []).length} references`, JSON.stringify(packet.included_sources ?? [], null, 2));
  recordCard(target, "Compiler metadata", "", JSON.stringify({compiler_version:packet.compiler_version, section_allocations:packet.section_allocations, transformations:packet.transformations, max_input_tokens:packet.max_input_tokens, reserve_output_tokens:packet.reserve_output_tokens, input_budget:packet.input_budget}, null, 2));
  if (Array.isArray(dropped) && dropped.length) recordCard(target, "Dropped context", `${dropped.length} omitted items`, JSON.stringify(dropped, null, 2));
}
async function loadMemory() {
  const target = $("#memory-content");
  target.replaceChildren();
  const params = new URLSearchParams({state: $("#memory-state").value, limit: "100"});
  if ($("#memory-scope").value) params.set("scope", $("#memory-scope").value);
  if (state.selectedProjectId) params.set("project_id", state.selectedProjectId);
  if (state.selectedConversationId) params.set("conversation_id", state.selectedConversationId);
  if (state.selectedBranchId) params.set("branch_id", state.selectedBranchId);
  const result = await api(`/v1/memory?${params}`);
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
  if (!(result.items ?? []).length) addText(target, "p", "muted", "No memory records match this filter.");
}
async function createMemory() {
  const content = window.prompt("Memory content");
  if (!content?.trim()) return;
  const scope = $("#memory-scope").value || (state.selectedProjectId ? "project" : "user");
  const kind = window.prompt("Memory kind: preference, fact, decision, goal, procedure, open_question, pattern", "fact");
  if (!kind) return;
  const scopeId = scope === "project" ? state.selectedProjectId : scope === "conversation" ? state.selectedConversationId : scope === "branch" ? state.selectedBranchId : null;
  if (["project","conversation","branch"].includes(scope) && !scopeId) {
    throw new Error(`Select a ${scope} before creating memory in that scope.`);
  }
  await api("/v1/memory", {method:"POST",body:{schema_version:1,scope,scope_id:scopeId,kind,content:content.trim(),importance:3,origin_kind:"user"}});
  await loadMemory();
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
async function showClaim(claimId) {
  const claim = await api(`/v1/claims/${encodeURIComponent(claimId)}${state.selectedProjectId ? "?project_id="+encodeURIComponent(state.selectedProjectId) : ""}`);
  const target = $("#claim-detail"); target.replaceChildren();
  addText(target,"h3","",claim.text);
  addText(target,"div","record-meta",`${claim.claim_type} · ${claim.project_id ? "project scoped" : "global"} · ${claim.origin_kind}`);
  const statuses = claim.current_status ?? [];
  recordCard(target,"Current status",statuses.map(x=>x.scope+": "+x.status).join(" · ") || "No status events","Status is scoped; this view does not infer truth.");
  const evidence = claim.evidence ?? [];
  const evidenceSection = recordCard(target,"Evidence",`${evidence.length} records`,"Sources linked to this claim.");
  for (const item of evidence) addText(evidenceSection,"p","record-body",`${item.stance}: ${item.excerpt ?? ""} ${item.locator ?? ""}`);
  const relations = claim.relations ?? [];
  const relationSection = recordCard(target,"Relationships",`${relations.length} links`,"Contradictions are compared side by side; other links remain listed by type.");
  for (const rel of relations) {
    const otherId = rel.from_claim_id === claim.id ? rel.to_claim_id : rel.from_claim_id;
    if (rel.rel === "contradicts") {
      try {
        const other = await api(`/v1/claims/${encodeURIComponent(otherId)}${state.selectedProjectId ? "?project_id="+encodeURIComponent(state.selectedProjectId) : ""}`);
        const comparison = document.createElement("div"); comparison.className = "contradiction-pair";
        recordCard(comparison,"Selected claim","",claim.text);
        recordCard(comparison,"Contradicting claim",rel.contradiction_basis ?? "basis unspecified",other.text);
        relationSection.append(comparison);
      } catch { addText(relationSection,"p","record-body",`Contradiction · ${otherId} (details unavailable in this scope)`); }
    } else addText(relationSection,"p","record-body",`${rel.rel} · ${otherId}`);
  }
  const assessments = claim.assessments ?? [];
  const assessmentSection = recordCard(target,"Assessments",`${assessments.length} records`,"Assessments are recorded independently of status.");
  for (const item of assessments) addText(assessmentSection,"p","record-body",`${item.dimension}: ${item.value_num ?? item.value_text ?? ""} ${item.rationale ?? ""}`);
  const statusButton=document.createElement("button"); statusButton.type="button"; statusButton.className="secondary-button"; statusButton.textContent="Record status";
  statusButton.addEventListener("click",async()=>{
    const status=window.prompt("Status: proposed, reported, inferred, corroborated, contested, accepted, rejected, superseded, unresolved, unknown","reported");
    if(!status)return;
    const payload={schema_version:1,status,scope:"default",rationale:"Recorded from desktop claims panel.",actor_kind:"user"};
    if(status==="accepted") payload.policy=window.prompt("Acceptance policy (required)");
    await api(`/v1/claims/${encodeURIComponent(claim.id)}/status${state.selectedProjectId ? "?project_id="+encodeURIComponent(state.selectedProjectId) : ""}`,{method:"POST",body:payload});
    await showClaim(claim.id);
  });
  target.append(statusButton);
}
async function createOpenQuestion() {
  const text=window.prompt("What question remains unresolved?");
  if(!text?.trim()) return;
  const related=window.prompt("Related claim ID (optional)") || null;
  await api("/v1/open-questions",{method:"POST",body:{schema_version:1,project_id:state.selectedProjectId||null,text:text.trim(),related_claim_id:related}});
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
}
async function deleteProviderKey() {
  const providerId=$("#key-provider").value;
  if(!providerId) return;
  await window.cog.deleteProviderApiKey(providerId);
  $("#provider-key-status").textContent="Saved key deleted.";
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
