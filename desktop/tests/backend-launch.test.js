import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

import { BackendSupervisor } from "../main/backend-supervisor.js";
import { createSseParser } from "../main/sse-parser.js";

const desktopDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(desktopDir, "..");
const fakeServerPath = path.join(desktopDir, "tests/fixtures/fake_provider_server.py");

test("desktop starts a loopback backend and completes an authenticated fake-provider chat", async () => {
  const dataDir = await mkdtemp(path.join(tmpdir(), "smh-tree-m8-"));
  const supervisor = new BackendSupervisor({
    repoRoot: repositoryRoot,
    backendDir: path.join(repositoryRoot, "backend"),
    dataDir,
    startupTimeoutMs: 30_000,
    argsFactory: ({ backendDir, port }) => [
      "run", "--project", backendDir, "python", fakeServerPath,
      "--host", "127.0.0.1", "--port", String(port),
    ],
  });

  try {
    const connection = await supervisor.start();
    const baseUrl = connection.baseUrl;
    assert.equal(new URL(baseUrl).hostname, "127.0.0.1");

    const unauthorized = await fetch(baseUrl + "/v1/health");
    assert.equal(unauthorized.status, 401);

    const headers = { Authorization: "Bearer " + connection.token };
    const health = await fetch(baseUrl + "/v1/health", { headers });
    assert.equal(health.status, 200);
    assert.equal((await health.json()).version, "0.8.1");

    const projectResponse = await fetch(baseUrl + "/v1/projects", {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Desktop test project" }),
    });
    assert.equal(projectResponse.status, 201);
    const project = await projectResponse.json();

    const conversationResponse = await fetch(baseUrl + "/v1/conversations", {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Fake provider chat", project_id: project.id }),
    });
    assert.equal(conversationResponse.status, 201);
    const conversation = await conversationResponse.json();

    const providers = await fetch(baseUrl + "/v1/providers", { headers });
    assert.deepEqual((await providers.json()).items.map((item) => item.id), ["fake"]);

    const models = await fetch(baseUrl + "/v1/providers/fake/models", { headers });
    assert.deepEqual((await models.json()).items, ["fake-model"]);

    const chatResponse = await fetch(
      baseUrl + "/v1/branches/" + conversation.root_branch_id + "/chat",
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({
          content: "Say hello",
          provider: "fake",
          model: "fake-model",
          allow_remote: false,
        }),
      },
    );
    assert.equal(chatResponse.status, 200);

    const events = [];
    const parser = createSseParser((event, data) => events.push({ event, data }));
    const reader = chatResponse.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      parser.push(decoder.decode(value, { stream: true }));
    }
    parser.push(decoder.decode());
    parser.end();

    assert.deepEqual(
      events.filter((item) => item.event === "token").map((item) => item.data.token),
      ["hello", " from ", "SMH-Tree"],
    );
    const completed = events.find((item) => item.event === "done");
    assert.ok(completed);
    assert.ok(completed.data.run_id);

    const messagesResponse = await fetch(
      baseUrl + "/v1/branches/" + conversation.root_branch_id + "/messages",
      { headers },
    );
    const messages = (await messagesResponse.json()).items;
    assert.deepEqual(messages.map((item) => item.role), ["user", "assistant"]);
    assert.equal(messages[1].content, "hello from SMH-Tree");

    const runResponse = await fetch(baseUrl + "/v1/runs/" + completed.data.run_id, { headers });
    assert.equal((await runResponse.json()).status, "succeeded");
  } finally {
    await supervisor.stop();
    await rm(dataDir, { recursive: true, force: true });
  }
});
