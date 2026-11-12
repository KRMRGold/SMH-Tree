import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

import { BackendSupervisor } from "../main/backend-supervisor.js";

const desktopDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(desktopDir, "..");

test("real backend binds to loopback and rejects requests without its launch token", async () => {
  const dataDir = await mkdtemp(path.join(tmpdir(), "smh-tree-m8-"));
  const supervisor = new BackendSupervisor({
    repoRoot: repositoryRoot,
    backendDir: path.join(repositoryRoot, "backend"),
    dataDir,
    startupTimeoutMs: 30_000,
  });

  let connection;
  try {
    connection = await supervisor.start();

    assert.equal(new URL(connection.baseUrl).hostname, "127.0.0.1");

    const unauthorized = await fetch(`${connection.baseUrl}/v1/health`);
    assert.equal(unauthorized.status, 401);

    const authorized = await fetch(`${connection.baseUrl}/v1/health`, {
      headers: { Authorization: `Bearer ${connection.token}` },
    });
    assert.equal(authorized.status, 200);

    const health = await authorized.json();
    assert.equal(health.status, "ok");
    assert.equal(health.version, "0.7.0");
  } finally {
    await supervisor.stop();
    await rm(dataDir, { recursive: true, force: true });
  }
});
