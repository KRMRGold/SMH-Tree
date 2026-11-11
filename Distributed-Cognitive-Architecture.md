# Distributed Cognitive Architecture
**Design Document — v0.4**

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

The underlying models become replaceable reasoning engines.

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


## 17. Overall Direction

The intended result is a modular cognitive platform built from interconnected knowledge, memory, conversation, and execution systems.

Its persistent graph infrastructure provides continuity and structure.

Its cognitive network actively investigates, interprets, maintains, and develops that information.

Its integration layer allows specialized frameworks, models, tools, and applications to cooperate without becoming inseparable.

The system should not depend on one enormous model, one database, one framework, or one application.

**The goal is to build an adaptable cognitive environment in which specialized components work together as a larger, continuously developing system.**
