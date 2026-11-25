# Distributed Cognitive Architecture
**Design Document — v0.8**

## 1. Vision

Build a modular, distributed cognitive architecture that allows multiple AI models, agents, knowledge systems, and applications to work together as a persistent, interconnected system.

The goal is to create something that behaves more like a continuously developing cognitive network than a single chatbot.

It should be able to:

- Maintain continuity across conversations, projects, and applications.
- Preserve and retrieve relevant information without requiring the entire conversation history.
- Organize knowledge into interconnected, evolving graphs.
- Identify relationships, contradictions, gaps, and unresolved questions.
- Delegate specialized tasks to different models and agents.
- Research information, evaluate sources, and communicate uncertainty.
- Recognize when it does not know something and direct users toward appropriate resources.
- Adapt its behavior and knowledge without requiring model retraining.
- Integrate existing software and services rather than unnecessarily recreating their functionality.

The architecture should remain modular, replaceable, extensible, and independent of any single model provider or framework.

## 2. Core Architectural Philosophy

The system combines two complementary approaches.

**Context-first infrastructure**

A persistent foundation for storing, organizing, retrieving, and assembling information. This infrastructure must remain useful even when background agents or specialized models are unavailable.

**Network-first cognition**

An active network of models, agents, and tools that investigates information, manages context, performs tasks, and develops relationships between knowledge.

Neither approach is sufficient by itself. The persistent infrastructure provides continuity; the cognitive network actively uses and develops that infrastructure.

### 2.1 Modular by Design

The system should not become one enormous framework with tightly coupled internal components.

Instead, it should consist of specialized subsystems connected through defined interfaces, APIs, shared data contracts, and communication protocols.

Each subsystem should:

- Have a clearly defined responsibility.
- Be independently usable where practical.
- Expose functionality through documented interfaces.
- Maintain its own internal implementation where appropriate.
- Exchange information through agreed-upon data structures.
- Be replaceable without requiring a complete architectural redesign.

Existing projects should be reused when they already provide suitable functionality. Our own development should concentrate on integration, coordination, and capabilities that existing projects do not adequately provide.

**The architecture owns the relationships between components, not necessarily their implementations.**

## 3. Overall Architecture

The system consists of three primary layers, supported by a persistent graph foundation and a modular integration layer.

### 3.1 Knowledge and Memory Layer

The persistent foundation. Responsible for storing and maintaining:

- Knowledge and concepts.
- Claims and evidence.
- Sources and provenance.
- Personal and project memory.
- Historical information.
- Relationships and dependencies.
- Unresolved questions and contradictions.
- Procedures and reusable knowledge.

### 3.2 Conversation and Task State Layer

Responsible for maintaining active interaction and continuity.

Includes conversations, messages, branches, participants, agents, current context, user intentions, active tasks, decisions, unresolved discussions, and task-specific state.

Conversation branches should inherit relevant history from their parent branch up to the point of divergence, then maintain independent developments.

### 3.3 Execution and Agent Network Layer

Responsible for actively operating on the other layers.

Includes language models, specialist agents, tools, external services, workflows, task delegation, checkpoints, execution history, research and verification processes, and context management and compilation.

This layer allows the system to investigate, reason, retrieve, update, and coordinate rather than simply retrieve stored information.

## 4. Graph Architecture

The system should use multiple interconnected graph representations rather than forcing every kind of information into one graph structure.

These graphs may share an underlying database, use separate storage systems, or combine both approaches. Their logical responsibilities should remain distinct regardless of physical storage.

### 4.1 Conversation Graph

Represents interaction history.

Objects include conversations, messages, branches, participants, agents, events, decisions, and references to external knowledge.

Relationships describe conversation order, branching, participation, references, and shared context.

### 4.2 Knowledge Graph

Represents information about the world and its relationships.

Objects include entities, concepts, events, claims, documents, sources, topics, and relationships.

It should support temporal information, multiple interpretations, competing claims, and source attribution.

### 4.3 Memory Graph

Represents retained information useful for continuity and future reasoning.

Objects include user preferences, experiences, decisions, goals, project context, relevant facts, procedures, unresolved questions, and learned patterns.

Memory should be scoped appropriately:

- Global.
- User.
- Project.
- Conversation.
- Branch.
- Agent.

Information should not automatically become globally accessible merely because it exists somewhere in the system.

### 4.4 Execution Graph

Represents how the system operates.

Objects include agents, models, tools, tasks, subtasks, workflows, checkpoints, results, and dependencies.

It should preserve enough execution history to understand what was attempted, what succeeded, what failed, and why.

### 4.5 Interconnected Graphs

These representations should be able to reference each other.

For example, a conversation message may introduce a claim. That claim may reference a source in the knowledge graph. A research agent may investigate it through an execution workflow. The result may update the knowledge graph and become relevant to a project memory.

The system should preserve these connections rather than flattening everything into disconnected summaries.

## 5. Epistemic Management Layer

A dedicated subsystem should manage what the system knows, believes, suspects, and does not know.

The architecture must distinguish between information being stored and information being established as reliable.

### 5.1 Separate Information Types

**Claims:** Statements that may be true, false, incomplete, disputed, or unverified.

**Evidence:** Information supporting or challenging claims, linked to its original sources.

**Arguments:** Reasoning structures connecting premises, assumptions, inferences, counterarguments, and conclusions.

**Evaluations:** Context-dependent assessments of evidence and arguments.

These should remain separate graph objects connected through explicit relationships.

### 5.2 Epistemic States

Potential states include proposed, reported, inferred, corroborated, contested, accepted, rejected, superseded, unresolved, and unknown.

These states should not be treated as one universal linear progression. A claim can be corroborated by several sources while remaining contested by another body of evidence.

Acceptance should always have a defined scope and evaluation policy.

### 5.3 Confidence and Reliability

Avoid relying on one universal confidence score. Track separate dimensions where possible:

- Source reliability.
- Evidence strength.
- Extraction reliability.
- Verification status.
- Temporal validity.
- Argument strength.

The system should be able to explain why it reached a conclusion.

### 5.4 Contradiction Management

Contradictions should be preserved rather than automatically resolved by choosing one statement.

The system should identify potentially conflicting claims, preserve their respective sources, determine whether they concern different times, contexts, or definitions, investigate competing explanations, record unresolved disagreements, and update evaluations when new evidence appears.

Contradictions should be localized so that uncertainty about one claim does not invalidate unrelated knowledge.

### 5.5 Provenance

Information should retain its origins and transformation history.

The system should distinguish original source material, extracted information, agent-generated interpretations, inferences, summaries, and verified results.

Derived information should reference the information and processes from which it originated.

Original material should remain canonical wherever practical. Summaries and interpretations are derived representations, not replacements.

## 6. Context Management

A dedicated context manager should determine what information is relevant to a particular interaction or task. It should not simply provide the entire stored memory to a model.

### 6.1 Context Compilation

The context compiler assembles a context packet appropriate to the model and task.

Potential inputs include system instructions, relevant user preferences, project information, conversation history, branch-specific context, retrieved knowledge, relevant claims and evidence, active task state, previous agent results, and unresolved questions.

The compiler should respect context limits, permissions, relevance, and information provenance. Different models may require different context formats.

### 6.2 Memory Maintenance

A background memory curator can identify potentially useful information, detect duplicates, identify outdated information, connect related concepts, suggest memory updates, preserve important decisions, and identify unresolved questions.

Memory maintenance should be asynchronous where possible. The system should remain functional without background agents running continuously.

### 6.3 Context Scoping

Context should be assembled according to its scope.

A branch should inherit relevant information from its parent but should not automatically absorb unrelated sibling-branch developments. Project memory should remain distinct from global memory. Agents should receive only the context necessary and authorized for their task.

## 7. Modular Technology Integration

The architecture should reuse established frameworks and services wherever they provide useful functionality.

Rather than merging their source code into one framework, the system should integrate them as independently replaceable components.

### 7.1 Candidate Components

**Graphiti — Temporal Knowledge Graph**

Potential responsibilities:

- Temporal entity and relationship management.
- Historical knowledge.
- Relationship retrieval.
- Hybrid graph and semantic search.
- Tracking how information changes over time.

Graphiti should be evaluated as a specialized temporal knowledge subsystem.

**Cognee — Knowledge Processing and Retrieval**

Potential responsibilities:

- Information ingestion.
- Knowledge extraction.
- Graph construction.
- Document processing.
- Semantic and graph retrieval.
- Knowledge enrichment.

Cognee should be evaluated for capabilities that complement the temporal graph rather than duplicating them unnecessarily.

**LangGraph — Execution and Orchestration**

Potential responsibilities:

- Agent workflows.
- Task delegation.
- Stateful execution.
- Checkpointing.
- Workflow recovery.
- Multi-step coordination.

LangGraph should manage execution rather than serve as the canonical knowledge graph.

**Neo4j or Another Graph Backend — Persistent Storage**

Potential responsibilities:

- Graph persistence.
- Relationship queries.
- Indexing.
- Constraints.
- Shared graph access where compatible.

The storage backend should remain replaceable where practical.

These are candidate integrations, not mandatory dependencies. Each should be tested against actual requirements before being adopted.

### 7.2 Integration Layer

A dedicated integration layer connects the different components.

It should provide:

- Common identifiers.
- Shared data contracts.
- API adapters.
- Permission enforcement.
- Event communication.
- Data transformation.
- Synchronization.
- Error handling.
- Version compatibility.

Applications and agents should interact with the architecture through stable interfaces rather than depending directly on the internal implementation of every subsystem.

### 7.3 Shared Data Contract

The system needs a common representation for information exchanged between components.

For example, a claim might contain:

- Unique identifier.
- Claim type.
- Subject, relationship, and object where applicable.
- Source references.
- Creation and observation timestamps.
- Temporal validity.
- Epistemic status.
- Verification information.
- Relationships to supporting or contradicting claims.
- Originating agent or process.

JSON with a versioned schema is a reasonable starting point.

Adapters translate between this shared representation and the native formats of integrated components.

The common contract should define meaning and relationships, not force every subsystem to use identical internal data structures.

### 7.4 Component Independence

Components should be replaceable.

For example, Graphiti could be replaced by another temporal graph system; Cognee could be replaced by another ingestion pipeline; LangGraph could be replaced by another orchestration framework; a model provider could be changed without redesigning memory; and the graph database could be migrated without rewriting applications.

This requires stable interfaces and clear ownership of data.

### 7.5 Data Ownership

Sharing a database does not mean every component owns every record.

Each subsystem should have defined write responsibilities.

For example:

- Graphiti manages its temporal knowledge operations.
- Cognee manages its ingestion and enrichment processes.
- LangGraph manages workflow execution state.
- The architecture manages canonical identifiers, permissions, epistemic rules, and cross-system coordination.

Where multiple systems need the same information, use explicit synchronization or shared read interfaces.

Do not assume that two systems sharing a database automatically provide safe bidirectional synchronization.

### 7.6 API-First Integration

The architecture should expose capabilities through documented APIs.

Potential interface categories include knowledge retrieval, memory retrieval and updates, conversation history, branch management, context compilation, agent execution, research requests, evidence verification, knowledge ingestion, and system status and capability discovery.

A component should be usable independently through its own interface when practical. This also allows separate applications to share the same cognitive infrastructure.

### 7.7 Tool interoperability and model adaptation

**Model Context Protocol (MCP)** is a standard interface through which compatible AI clients can discover and invoke tools, and access other explicitly exposed context. It is an interoperability layer, not a model, agent framework, database, or replacement for the platform's own API.

For SMH-Tree, a future MCP adapter could expose selected platform capabilities to external AI clients or agent runtimes, for example:

- Search authorized project context and knowledge.
- Retrieve conversation or branch history.
- Read selected claims, sources, and evidence.
- Start an explicitly permitted workflow.
- Propose a memory or knowledge update for user review.

The intended boundary is:

```text
AI client / agent
       |
   MCP adapter
       |
SMH-Tree application API
       |
services, permissions, context compiler, and canonical SQLite data
```

The existing application API and backend remain authoritative. MCP should adapt stable application operations into discoverable tools; it should not become a second business-logic layer or access SQLite directly. The same backend authorization, project/branch scope checks, validation, provenance, remote-use rules, and audit requirements must apply whether an operation arrives through the desktop UI, the API, or MCP. Mutating capabilities should be narrowly allowlisted, with consequential actions requiring the appropriate user authorization. An MCP connection must not implicitly grant access to all stored context or permit arbitrary filesystem, shell, or database access.

MCP is optional. It is most useful when SMH-Tree needs to interoperate with multiple external AI clients or agent systems. The desktop application can continue calling its own backend API directly; it does not need to route every internal operation through MCP.

**Model training tools are a separate concern.** Soup is an example of a model-development toolkit for preparing datasets, fine-tuning and evaluating models, and serving trained models through an API. Its own MCP server exposes Soup operations to compatible clients; that does not make Soup itself an MCP alternative, nor does it automatically expose SMH-Tree's data or capabilities. A future SMH-Tree deployment could optionally use a Soup-trained model through a compatible model-provider adapter, while using a separate SMH-Tree MCP adapter to expose platform tools.

Training or fine-tuning should remain an optional model lifecycle capability, not a foundational dependency. Prefer the existing adaptation mechanisms—context compilation, persistent memory, versioned instructions, retrieval, tools, and workflow changes—when they solve the problem. Consider fine-tuning only when evaluations show a persistent behavior gap that cannot be addressed adequately through those mechanisms and when suitable training data, compute, evaluation, and model distribution are available. A trained model must remain replaceable and must not own canonical project knowledge or permissions.

These are future interoperability and experimentation options, not MVP scope or an adoption decision. Evaluate them against concrete use cases before implementation.


#### Model adaptation lifecycle: teacher, student, and specialist models

The model ecosystem may optionally improve local models by using a more capable model as a **teacher** and a smaller or more efficient model as a **student**. This is a development-time workflow, not a requirement that every request consult a large model.

A teacher may help produce candidate examples, demonstrate target behavior, critique student outputs, or provide evaluation signals. Curated examples can then be used for supervised fine-tuning or knowledge distillation. Parameter-efficient approaches such as LoRA/QLoRA may be preferable to full fine-tuning when they meet the target quality and hardware constraints. Synthetic examples are candidate training material, not ground truth: they need provenance, quality checks, and representative human or deterministic review before being promoted into a training set.

Keep the responsibilities distinct:

- **Model Manager:** discovers and manages installed/loaded inference models and their runtime availability.
- **Model Router:** chooses an eligible model for a particular inference task.
- **Model Adaptation Pipeline:** optionally prepares versioned datasets, runs or delegates adaptation jobs, evaluates candidate artifacts, and promotes or rolls back model versions. It does not own inference routing or canonical project data.
- **Teacher/evaluator roles:** temporary roles that may be fulfilled by an existing local or remote model; they are not permanently bound to a specific provider or model.

Use the least complex mechanism that closes the measured gap. Try prompt and schema improvements, better context, retrieval, tools, and workflow changes first. Use RAG or the existing knowledge/memory stores for information that changes, needs citations, or must remain inspectable. Consider fine-tuning when a stable task behavior remains unreliable across representative cases. Consider distillation when a capable teacher demonstrates a repeatable capability that a smaller candidate fails to reproduce and the smaller candidate is worth deploying for latency, memory, cost, or offline use.

A candidate adaptation cycle should:

1. Define the target capability and measurable acceptance criteria.
2. Capture a baseline using representative held-out tasks and relevant regression checks.
3. Diagnose whether the gap belongs to the model, instructions, context, retrieval, tools, or execution workflow.
4. Prepare a versioned dataset with source/provenance, permission, quality, and privacy checks. Teacher-generated examples must be labeled as synthetic and reviewed; remote teacher use remains subject to the existing per-request remote gate and transmission audit.
5. Select the lightest suitable method (for example, supervised fine-tuning, LoRA/QLoRA, or teacher-to-student distillation) and record the base model, training configuration, dataset revision, and resulting artifact identity.
6. Evaluate the candidate against the same held-out target set and broader regression checks, including instruction following, structured/tool output, safety behavior, and unrelated capabilities likely to be affected.
7. Promote only after the candidate meets the acceptance criteria; retain the previous eligible model/adapter and a clear rollback path.

Training data and model artifacts must not silently absorb private conversation history, user memory, secrets, or project records. Apply scope and remote-sharing permissions before any teacher or training service receives data. A model's learned behavior is not a substitute for the canonical SQLite record, scoped memory, epistemic provenance, retrieval, or access control. Do not train changing facts, permissions, user preferences, or project state into weights when those belong in external, updateable sources.

Model routing should compare measured task suitability alongside model capabilities, context limits, modality and tool-call reliability, local RAM/VRAM and quantization requirements, latency, availability, user preference, and remote-processing permission. Hardware fit and evaluation evidence matter more than parameter count or model name. A small specialist model can be useful when paired with reliable application APIs and capability contracts: the model interprets and coordinates intent; the application performs exact operations and reports structured results.

Adaptation is optional and evidence-driven. It must not become a prerequisite for SMH-Tree's core memory, retrieval, tool, or workflow capabilities, and a trained model must remain replaceable. These are post-M10 design options, not an implementation or training decision.


### 7.8 Capability-Oriented Task Execution

The integration layer should expose application and domain capabilities as discoverable, versioned contracts. A capability describes an operation that an agent can request without binding that operation permanently to one model or agent.

A capability definition should identify:
- Stable capability and operation identifiers.
- Description, input/output schemas, and version.
- Required application, runtime, provider, or external service.
- Required model abilities, such as vision, tool calling, long context, or structured output.
- Preconditions, application-state requirements, and expected side effects.
- Permission scope, risk classification, and user-approval requirements.
- Validation and verification procedures.
- Relevant skills, instructions, examples, and known limitations.

Capabilities may be implemented through MCP servers, native application APIs, command interfaces, or other adapters. MCP is one transport and discovery mechanism, not the capability registry itself. The registry should normalize metadata and expose a stable contract regardless of implementation.

The registry describes what can be done; it does not itself authorize execution. Authorization remains enforced by the backend and the relevant application adapter.

### 7.9 Task, Agent, Model, and Capability Routing

Routing responsibilities should remain distinct:

- **Task/Agent Router:** Selects an appropriate specialist role or workflow for the requested outcome.
- **Model Router:** Selects an eligible model/provider based on task requirements, model profiles, availability, resource constraints, user preferences, and remote-processing permissions.
- **Capability Router:** Resolves the application operations and integrations required to perform the task.
- **Execution Manager:** Coordinates dependencies, checkpoints, retries, cancellation, result collection, and recovery.

A specialist agent is a role definition, not a dedicated model instance. It may use an existing model with role instructions, scoped context, skills, and capabilities. Model fine-tuning is optional and should be considered only when evaluation demonstrates a persistent behavior gap that prompting, context, retrieval, tools, or workflow changes do not adequately address.

A task plan should be inspectable before consequential execution. It should identify the intended operations, affected resources, dependencies, required permissions, expected outputs, and verification criteria. The system should be able to pause for clarification or approval rather than silently guessing.

### 7.10 Interactive Application State and Human-Guided Editing

Application integrations should support bidirectional interaction rather than one-way command execution.

The integration should be able to retrieve relevant application state, perform authorized operations, and report resulting state changes. Depending on the application, state may include selected objects, geometry, transforms, constraints, timeline position, tracks, keyframes, layers, effects, camera settings, or active document identifiers.

The user should be able to intervene directly in the native application and provide structured guidance such as:
- Selecting an object, region, track, layer, or timeline range.
- Moving or adjusting an element manually.
- Adding annotations, guides, reference points, or constraints.
- Changing parameters through the application's own controls.
- Accepting, rejecting, or refining a proposed operation.

The application adapter should report the resulting state or a scoped state diff so the agent can continue from the user's actual edits. Screenshots may supplement this information but should not replace structured application state when the application exposes it.

**Targeted modification is the default.** Agents should issue narrow operations or patches against identified resources rather than regenerate or replace an entire project. User-authored changes must be treated as authoritative current state unless the user explicitly requests otherwise. Before applying a patch, the executor should detect stale state or conflicting edits and request reconciliation where necessary.

#### Shared attention and progressive precision

The user should be able to act on their own intuition at any project scale without having to translate every detail into technical terminology or reconstruct the surrounding context in a prompt. Conversation is one interface to a shared cognitive workspace, not the only means of interaction.

- Support deictic communication: pointing, selecting, highlighting, drawing arrows or regions over a screenshot or live view, and accompanying these gestures with text or speech (for example, "move this here").
- Make shared attention bidirectional. Agents should be able to highlight referenced objects, dependencies, alternative placements, and affected regions for the user to inspect and correct.
- Ground references in stable application/object identifiers, artifact revisions, view coordinates and transforms, selection scope, and relevant state. Preserve annotations as separate layers; a screenshot alone is not authoritative application state. Where grounding is uncertain, present candidates or ask for clarification rather than silently editing.
- Allow progressive precision: move freely between broad natural-language intent, visual annotation, direct manipulation, exact property values, and source-level editing. These interfaces should operate on the same underlying artifact rather than divergent copies.
- Integrate reusable property inspectors where available, using application-specific adapters (including MCP where appropriate). Prefer deterministic property updates or constraint solving for exact edits; use models for ambiguous intent and semantic grounding.
- Distinguish instance, component, page, project and shared-definition scope. Preview affected objects and proposed changes, preserve unrelated state, detect conflicting revisions, and provide undo or recoverable checkpoints where supported.
- Persist meaningful object references and associated discussion, decisions, edits and provenance in the appropriate project/branch scope. Selecting an object later should allow retrieval of its relevant history without loading the entire project or treating stale references as current state. Handle renamed, moved and deleted objects explicitly.

Examples include marking a website layout, sketching a 3D silhouette or animation path, selecting a waveform or timeline range, highlighting writing passages, and manipulating knowledge graph relationships. The interaction contract should be shared, while grounding, editing and verification remain domain-specific.

Prior art to evaluate:
- [Put-That-There](https://doi.org/10.1145/800250.807503): speech and pointing, deictic interaction.
- [Sketch-n-Sketch](https://ravichugh.github.io/sketch-n-sketch/): output-directed and bidirectional programming.
- [Design Mode](https://github.com/SandeepBaskaran/design-mode): visual web editing and agent integration.
- [Onlook](https://github.com/onlook-dev/onlook): visual editing of application code.
- [DragDiffusion](https://github.com/Yujun-Shi/DragDiffusion): point-directed image manipulation; distinguish pixel-level generation from structured artifact editing.

Suggested post-MVP prototype: one browser adapter supporting element selection, screenshot annotation, stable element references, reciprocal highlighting, property inspection, scoped patches and preview/undo. Evaluate reference resolution accuracy, scope errors, preservation of unrelated state, revision conflicts, context retrieval and user effort before generalizing to other applications. These are research candidates, not adopted dependencies or new milestone acceptance requirements.

### 7.11 Execution Provenance and Verification

Application operations should be represented in the execution graph with their task, agent, model/provider, capability and operation identifiers, input references, target resources, permission decision, result, and verification outcome.

Where practical, preserve:
- A pre-operation state reference or recoverable checkpoint.
- The exact operation parameters and affected resource identifiers.
- A post-operation state reference or diff.
- User approvals and manual interventions.
- Validation results, warnings, and unresolved uncertainty.

Verification should be application- and domain-specific. Examples include geometry and tolerance checks in CAD, object and constraint checks in 3D scenes, timeline and media-reference checks in video editing, and signal/routing checks in audio or electronics workflows. A successful API call or visually plausible render is not proof that the requested result is correct.

The system should distinguish operation success, application validity, requirement satisfaction, and user acceptance. These are separate outcomes.

### 7.12 Security and Execution Boundaries

Capability invocation must use the existing application API, permission model, and audit boundaries. An MCP server or specialist agent must not bypass authorization by accessing canonical storage or unrestricted host resources directly.

Capabilities should be scoped to the user, application, project, conversation, branch, agent, and external service as appropriate. Consequential or destructive operations should require explicit approval according to their risk and configured policy. Filesystem, shell, network, and application scripting access must be narrowly allowlisted.

Remote model selection must continue to obey the per-request remote gate. Routing must not silently transmit project files, application state, or context to an external provider. The actual model/provider, capability calls, approvals, and data transfers should remain inspectable in execution provenance.

These capabilities are post-MVP architectural extensions. They do not expand M0–M10 acceptance scope.

## 8. Cognitive Network

The architecture should support specialized agents rather than relying on one model to perform every task.

Potential agent responsibilities include:

- **Memory Curator:** Maintains useful retained information and identifies outdated or duplicated memories.
- **Context Retriever:** Finds relevant information for the current task.
- **Research Agent:** Investigates questions using external resources and stored knowledge.
- **Verification Agent:** Checks claims, evidence, source reliability, and conflicting information.
- **Argumentation Agent:** Develops and evaluates competing explanations and reasoning structures.
- **Knowledge Manager:** Maintains relationships, identifies gaps, and coordinates knowledge updates.
- **Task Coordinator:** Delegates work and manages dependencies.
- **Context Compiler:** Assembles the information required by the active model.
- **Continuity Agent:** Identifies relevant previous decisions, conversations, and unfinished work.

Agents should be independently replaceable and should not require the same model.

### 8.1 Deterministic and Model-Based Responsibilities

Use ordinary software for operations that should be predictable:

- Permissions.
- Data validation.
- Identifier management.
- Token counting.
- Database queries.
- Deduplication where exact matching is sufficient.
- Versioning.
- Workflow state.
- Synchronization.

Use models where interpretation is needed:

- Semantic extraction.
- Relationship discovery.
- Ambiguous information.
- Research synthesis.
- Argument evaluation.
- Context relevance.
- Natural-language interaction.

Models should not be given authority over operations that can be reliably enforced by deterministic code.

## 9. Adaptation Without Retraining

The system should develop capabilities primarily through its external infrastructure.

Rather than requiring model retraining whenever something changes, the architecture can adapt through persistent memory, updated knowledge graphs, new skills and procedures, improved retrieval, better context assembly, specialist agents, tool integrations, updated workflows, and accumulated evaluations and feedback.

The underlying models become replaceable reasoning engines. Fine-tuning may be used as an optional way to improve a model's task behavior, but it is not the default mechanism for keeping the platform current; persistent context, retrieval, tools, and workflows should carry changing project knowledge.

A better model can be introduced without discarding the accumulated knowledge and operational infrastructure. Likewise, an individual model can be replaced without losing conversation continuity.

## 10. Uncertainty and External Resources

The system should not be pressured to generate an answer when reliable information is unavailable.

It should be able to:

- Say that it does not know.
- Explain what is uncertain.
- Identify what information is missing.
- Distinguish established information from speculation.
- Search for additional evidence.
- Identify relevant external resources.
- Provide references for verification.
- Recommend appropriate specialists or primary sources when needed.

The architecture should make uncertainty an explicit part of its knowledge model rather than treating it as a weakness to conceal.

## 11. Application Integration

The cognitive infrastructure should be independent of individual applications. Applications become interfaces and specialized environments that use the shared architecture.

**Chatapp**

Potential integration: multiple character or assistant models, shared context and memory, specialist agent participation, persistent knowledge, group collaboration, and local model support.

**C-2 Branching Messenger**

Potential integration: shared conversation infrastructure, branch-aware context, independent conversation histories, AI participation in conversations, knowledge references across branches, and optional shared cognitive services.

**Meta-Modules**

Potential integration: reusable procedural knowledge, discoverable instruction modules, agent capabilities and workflows, externalized operational instructions, and versioned skills and procedures.

These projects should not be merged into one application. They can remain independent projects that connect to the same cognitive infrastructure.

## 12. Security and Permissions

The architecture should support explicit access boundaries.

Potential scopes include user, application, project, conversation, branch, agent, and external service.

Agents should only access information authorized for their task.

The architecture should distinguish between information being available in storage and information being permitted in a particular context.

Local, self-hosted, and remote deployments should be considered. Sensitive information should not automatically be sent to external models or services.

## 13. Development Strategy

Development should proceed incrementally, validating the architecture before introducing unnecessary complexity.

### Phase 1 — Common Foundation

- Define core entities and relationships.
- Establish identifiers and provenance.
- Define the four graph representations.
- Define the shared data contract.
- Establish permissions and scopes.
- Evaluate graph storage options.

### Phase 2 — Knowledge and Memory

- Prototype temporal knowledge management.
- Implement claim and evidence relationships.
- Add contradiction tracking.
- Test graph retrieval.
- Introduce ingestion and enrichment.
- Establish memory scopes.

### Phase 3 — Context and Conversation

- Implement conversation and branch persistence.
- Build context compilation.
- Integrate memory retrieval.
- Test context continuity.
- Test branch isolation and inheritance.

### Phase 4 — Cognitive Network

- Introduce agent orchestration.
- Implement specialist agents.
- Add research and verification workflows.
- Add execution checkpoints.
- Test recovery and delegation.

### Phase 5 — Integration

- Connect Chatapp.
- Connect C-2.
- Connect Meta-Modules.
- Introduce additional applications through the API.
- Test independent component replacement.

### Phase 6 — Continuous Development

- Improve knowledge maintenance.
- Develop more sophisticated reasoning and argument evaluation.
- Improve retrieval and context relevance.
- Expand agent capabilities.
- Evaluate alternative frameworks and models.

## 14. Design Principles

1. **Modularity:** Components should be independently replaceable.
2. **Interoperability:** Systems communicate through documented contracts.
3. **Continuity:** Knowledge and context persist beyond individual conversations.
4. **Provenance:** Information retains its origins and transformation history.
5. **Epistemic integrity:** Claims, evidence, and conclusions remain distinguishable.
6. **Temporal awareness:** Knowledge can change without erasing its history.
7. **Branch independence:** Divergent conversations maintain their own context.
8. **Model independence:** The architecture is not tied to one model or provider.
9. **Graceful degradation:** The system remains useful when individual components are unavailable.
10. **Transparency:** The system can explain its conclusions and uncertainty.
11. **Extensibility:** New applications, agents, and services can be integrated without redesigning the entire platform.
12. **Practical reuse:** Existing solutions should be adopted when they solve a problem adequately.

## 15. Open Questions

The following require further investigation before implementation decisions are finalized:

- Which graph database best supports the combined requirements?
- Which Graphiti and Cognee capabilities overlap, and which complement each other?
- Which components should share storage?
- What synchronization model should be used between subsystems?
- What should the canonical data contract contain?
- How should permissions propagate between applications and agents?
- How should the architecture handle offline operation?
- How should agent results be evaluated before becoming persistent knowledge?
- How should conflicting information be surfaced to users?
- What should remain local versus use external services?
- How should component versions and schema migrations be managed?


## 16. Desktop Application and Technology Stack

The initial user-facing implementation will be a **Windows-first desktop application** with hybrid local and online operation.

The desktop application should remain useful without an internet connection. Local application data and locally available capabilities should continue working offline, while remote model providers and external research services add optional capabilities when connectivity is available.

Local storage is the default source of truth. Remote AI access must not imply automatic cloud synchronization or permission to transmit all stored information.

### 16.1 Desktop Shell

**Electron**

Responsibilities:

- Provide the Windows desktop application and native application lifecycle.
- Launch, supervise, and stop the local cognitive backend.
- Manage application-level permissions and the restricted bridge to the renderer.
- Package the application for Windows distribution.

**Frontend:** HTML, CSS, and vanilla JavaScript using native ES modules. Vite may be used for frontend development and builds. Electron Forge is the initial packaging candidate.

The renderer should not have unrestricted access to Node.js or local system resources. Use a restricted preload API, context isolation, renderer sandboxing, and disabled Node integration. Expose only the specific operations the interface needs.

### 16.2 Cognitive Backend

**Python** is the initial backend language because the selected knowledge-processing and agent-orchestration ecosystem is strongly Python-oriented.

Candidate components:

- **FastAPI:** local application API.
- **Pydantic:** request, response, and shared-contract validation.
- **LangGraph:** stateful agent workflows, delegation, and execution checkpoints.
- **uv:** Python dependency and environment management.

Start with one local Python backend process divided into clearly separated modules. Do not begin with multiple independently deployed microservices. Separate services can be introduced later if scaling, isolation, or deployment requirements justify them.

### 16.3 Storage Strategy

**SQLite is the initial canonical application database.**

Use it for conversations, messages, branches, task and execution metadata, settings, project metadata, epistemic records, and references to source material. SQLite FTS5 is a candidate for local full-text search.

Keep large source documents and attachments in the filesystem where practical, with their metadata, identifiers, and provenance references stored in SQLite.

A dedicated graph database is **not** a prerequisite for the first desktop prototype. The initial data model should represent entities and relationships in a way that can later be migrated or synchronized with a specialized graph backend.

Candidate knowledge components:

- **Cognee:** prototype ingestion, extraction, enrichment, and retrieval. Evaluate its storage-backend options, persistence model, and compatibility with the architecture's canonical identifiers before adopting it.
- **Graphiti:** retain as a candidate temporal knowledge subsystem. Its graph backend and Windows deployment requirements must be evaluated before making it a required dependency.
- **Dedicated graph database:** defer selection until a concrete prototype demonstrates which graph capabilities cannot be handled adequately by the initial storage layer.

Do not assume that Cognee and Graphiti should both be adopted. Establish which responsibilities complement each other and avoid duplicated ownership or implicit bidirectional synchronization.

### 16.4 Model Provider Layer

Use a provider-adapter interface so models and runtimes can be changed without redesigning the knowledge and conversation infrastructure.

Initial candidates:

- **Ollama:** local model runtime.
- **Remote model APIs:** optional online providers.
- **Embedding models:** independently configurable from conversational models.

Different tasks may use different models, including conversation, extraction, research, verification, embeddings, and lightweight background processing.

Each task should declare whether remote processing is allowed. Local information must not be sent to a remote provider merely because that provider is configured.

### 16.5 Desktop-to-Backend Communication

The Electron application and Python backend should communicate through a versioned local API.

Initial approach:

- HTTP with JSON for ordinary requests and responses.
- Server-Sent Events (SSE) for streamed model and agent output.
- WebSockets only if later requirements need bidirectional real-time communication.
- OpenAPI documentation and versioned schemas for the API contract.

The local backend should bind to loopback (127.0.0.1) by default, use a per-launch authentication token, and not expose its API to the local network unless an explicit future configuration enables that behavior.

Electron's main process should manage the backend process lifecycle. The renderer should communicate through the restricted preload bridge rather than directly accessing local databases, credentials, or arbitrary backend capabilities.

### 16.6 Windows Packaging and Data Locations

Candidate packaging approach:

- **Electron Forge** for the desktop application.
- **PyInstaller** to package the Python backend as a sidecar executable.
- Separate Windows builds and installers.
- User data stored outside the application installation directory.
- Model downloads and model storage managed independently from application updates.

Packaging the Python environment and its dependencies must be tested early. Native dependencies and the size of the knowledge-processing stack may complicate distribution. Do not bundle large AI models into the application installer.

### 16.7 Testing and Development Tooling

Initial candidates:

- **pytest:** Python backend tests.
- **Node.js built-in test runner:** frontend and application-side unit tests.
- **Playwright:** desktop UI and end-to-end testing, subject to validating the chosen Electron integration.
- **Git:** source history and development provenance.

The Python backend should be testable independently of Electron. This preserves the possibility of adding a web interface or other clients later.

### 16.8 Operating Modes

The application should distinguish local capabilities from online capabilities.

**Available offline, subject to local components being installed:**

- Open, create, and search local conversations.
- Read and update local memory and knowledge records.
- Navigate conversation branches.
- Run locally installed models.
- Execute workflows that do not require external services.

**Available when online:**

- Use configured remote model providers.
- Perform external research and retrieve online sources.
- Access future synchronization services if explicitly configured.

Cloud synchronization is a separate architectural decision. Hybrid AI access does not itself require account-based cloud storage or automatic synchronization.

### 16.9 Initial Architecture

The first Windows implementation follows this structure:

```text
Windows Desktop Application
└── Electron
    ├── Renderer: HTML / CSS / JavaScript
    ├── Preload: restricted application bridge
    └── Main Process
        └── Local Python Backend
            ├── FastAPI and Pydantic
            ├── LangGraph execution
            ├── Knowledge integration adapters
            │   ├── Cognee prototype
            │   └── Graphiti evaluation
            ├── SQLite canonical application data
            └── Model provider adapters
                ├── Ollama (local)
                └── Remote model APIs (optional)
```

This is a proposed initial stack, not a commitment to keep every candidate. Components should be adopted only after their integration, persistence, security, and packaging behavior have been tested.

### 16.10 Deferred Decisions and Risks

The following remain open:

- Which graph database, if any, should become the production desktop backend?
- Whether Cognee's capabilities and persistence model fit the canonical data contract.
- Whether Graphiti is worth the additional graph-backend deployment requirement.
- How Python dependencies and native components will be packaged and updated on Windows.
- How local model installation, selection, and resource requirements should be presented.
- Whether and how cloud synchronization should work.
- Which remote providers should be supported initially.
- How local data permissions and remote-transmission policies should be exposed to users.

The first technical prototype should validate the Electron-to-Python process lifecycle, local API security, SQLite persistence, one local model request, and one optional remote model request. Knowledge-framework integration and packaging should be tested as separate risks before they become foundational dependencies.


### 16.11 Local model lifecycle and request routing

Model lifecycle management and request routing are separate responsibilities built on the provider-adapter layer.

**Model Manager**

- Detect whether the configured local runtime (initially Ollama) is reachable.
- Discover installed models and separately report models currently loaded in runtime memory.
- Offer explicit load and unload operations for installed models.
- Expose provider-neutral status to the desktop UI while keeping runtime-specific lifecycle calls inside the Ollama adapter.
- Initially connect to an existing Ollama service rather than launching, stopping, installing, or updating the Ollama server itself.
- Do not download models automatically. Model acquisition remains a deliberate user action.
- Report lifecycle errors and runtime-reported resource information where available. Do not promise that every model can remain loaded simultaneously.

**Model Router**

The router selects a provider/model for each new task; it does not generate the answer. Its inputs include:

- Task category and required capabilities or modalities.
- Explicit model profiles and configured context limits.
- User-selected default, one-message override, or conversation-level pin.
- Provider/model availability and current runtime state.
- Local resource constraints and request concurrency.
- Per-request remote permission.

Start with deterministic rules and explicit user-editable profiles. Add optional model-based task classification only after the deterministic router is reliable. A classifier may recommend a task category or candidate model, but deterministic policy retains authority over permissions, model eligibility, fallback, and resource constraints.

**Selection precedence**

1. A valid one-message override.
2. A valid conversation-level pinned model.
3. Deterministic automatic selection using task requirements and eligible model profiles.
4. The configured eligible default/fallback.
5. A clear actionable error if no permitted model can handle the request.

An unavailable or incompatible explicit choice should be surfaced rather than silently ignored. Any fallback behavior must be visible to the user.

**Transparency and provenance**

Every run should record the actual provider/model used, whether selection was manual, pinned, or automatic, and a concise selection reason. The UI should make the selected model visible and allow the user to override it. Changing models affects future requests only; it does not rewrite previous messages or context snapshots.

**Remote and local boundaries**

The existing remote-transmission gate remains authoritative. Automatic routing cannot grant remote permission, expose disallowed memory, or bypass the transmission audit. A local model is preferred when remote use is not explicitly allowed. If no eligible local model exists, explain the limitation instead of silently sending the request remotely.

**Resource-aware lifecycle**

Keep-warm and idle-unload policies are later refinements. Begin with explicit load/unload controls and runtime-reported status. Add automatic unloading or preloading only after testing memory pressure, model-switch latency, and concurrent requests. Never assume all installed models fit in memory.

### 16.12 Compute-adaptive inference and looped model research

Research reference: [Thinking Machines Lab — Inkling 2 Mini](https://thinkingmachines.ai/news/inkling-2-mini/). Treat reported results as research evidence to investigate, not independently reproduced performance or a dependency decision.

Looped/recurrent transformer architectures reuse model weights across internal processing passes, potentially increasing effective computational depth without proportional weight storage growth. This complements the teacher/student and specialist adaptation lifecycle in §7.7 and the resource-aware router in §16.11.

Post-MVP implementation candidates:

- Extend model profiles with supported reasoning controls, fixed or adjustable internal depth, total and active parameter counts, quantization, context limits, estimated memory requirements, and runtime compatibility. Unknown capabilities remain unknown; do not infer adjustable depth from a model being looped.
- Introduce optional per-task compute budgets (latency, output tokens, memory, and provider-supported reasoning effort or loop count). Start with explicit user presets and deterministic routing; adaptive selection is a later experiment.
- Keep internal model recurrence separate from external agent iteration, tool calls, verification, and persistent memory. Repeated internal processing is not durable knowledge retention and should not replace the context compiler or memory graph.
- Compare conventional, sparse/MoE, looped, distilled, and specialist models under equivalent hardware and task conditions. Active parameters are not the total weight footprint; account for KV cache, runtime overhead, CPU offloading, and model-switch costs.
- Where supported, evaluate escalating compute on the same model before switching to a larger model or invoking a specialist. Enforce cancellation, bounded retries, resource ceilings, and the existing remote permission gate. Never silently escalate to remote processing.
- Evaluate teacher/student distillation and expert pruning as optional offline research paths when task-specific evidence justifies them; check licensing, data provenance, and regression risks before training.

Record requested and effective reasoning settings where exposed, actual model/runtime version, quantization, latency, peak RAM/VRAM, task success, tool-call validity, instruction adherence, and factual reliability. Compare quality against resource cost on representative SMH-Tree workloads, including context retrieval, branch continuity, structured tool calls, and verification. Do not equate longer reasoning with better answers or claim access to hidden internal reasoning.

Suggested sequence: capability discovery and profiling; reproducible local evaluation; explicit compute presets; bounded adaptive routing only if measurements show a benefit. Preserve model independence and existing acceptance scope (M0–M10). No particular model or inference runtime is required by this proposal.

## 17. Overall Direction

The intended result is a modular cognitive platform built from interconnected knowledge, memory, conversation, and execution systems.

Its persistent graph infrastructure provides continuity and structure.

Its cognitive network actively investigates, interprets, maintains, and develops that information.

Its integration layer allows specialized frameworks, models, tools, and applications to cooperate without becoming inseparable.

The system should not depend on one enormous model, one database, one framework, or one application.

**The goal is to build an adaptable cognitive environment in which specialized components work together as a larger, continuously developing system.**
