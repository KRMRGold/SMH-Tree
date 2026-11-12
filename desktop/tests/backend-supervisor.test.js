import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { test } from "node:test";

import {
  BackendSupervisor,
  findFreeLoopbackPort,
} from "../main/backend-supervisor.js";

class FakeChild extends EventEmitter {
  constructor(pid) {
    super();
    this.pid = pid;
    this.exitCode = null;
    this.signalCode = null;
  }
}

function createSupervisor(overrides = {}) {
  const children = [];
  const launches = [];
  const killed = [];
  let port = 43100;

  const supervisor = new BackendSupervisor({
    repoRoot: "/repo",
    backendDir: "/repo/backend",
    dataDir: "/user-data",
    command: "uv",
    spawnProcess: (command, args, options) => {
      const child = new FakeChild(1000 + children.length);
      children.push(child);
      launches.push({ command, args, options });
      return child;
    },
    fetchImpl: async (_url, options) => {
      assert.match(options.headers.Authorization, /^Bearer [a-f0-9]{64}$/);
      return { ok: true, status: 200 };
    },
    tokenFactory: () => "a".repeat(64),
    portFactory: async () => port++,
    sleep: async () => {},
    startupTimeoutMs: 50,
    killTree: async (child, platform) => {
      killed.push({ child, platform });
      child.exitCode = 0;
    },
    ...overrides,
  });

  return { supervisor, children, launches, killed };
}

test("chooses an available port bound only to loopback", async () => {
  const port = await findFreeLoopbackPort();
  assert.equal(Number.isInteger(port), true);
  assert.ok(port > 0 && port <= 65535);
});

test("starts the backend on loopback with a fresh 32-byte token", async () => {
  const { supervisor, launches, children, killed } = createSupervisor();
  const connection = await supervisor.start();

  assert.equal(connection.baseUrl, "http://127.0.0.1:43100");
  assert.equal(connection.token, "a".repeat(64));
  assert.equal(launches.length, 1);
  assert.deepEqual(launches[0].args.slice(-4), [
    "--host",
    "127.0.0.1",
    "--port",
    "43100",
  ]);
  assert.equal(launches[0].options.env.COGPLAT_API_TOKEN, "a".repeat(64));
  assert.equal(launches[0].options.env.COGPLAT_DATA_DIR, "/user-data");

  await supervisor.stop();
  assert.equal(killed.length, 1);
  assert.equal(killed[0].child, children[0]);
});

test("kills a backend that never becomes healthy", async () => {
  let killed = false;
  const { supervisor } = createSupervisor({
    fetchImpl: async () => { throw new Error("not ready"); },
    startupTimeoutMs: 1,
    sleep: async () => {},
    killTree: async () => { killed = true; },
  });

  await assert.rejects(supervisor.start(), /did not become ready/);
  assert.equal(killed, true);
});

test("restarts once after a crash and reports a second crash", async () => {
  const fatalErrors = [];
  const { supervisor, children, launches } = createSupervisor({
    onFatal: (error) => fatalErrors.push(error),
  });

  await supervisor.start();
  children[0].emit("exit", 1, null);
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(launches.length, 2);
  assert.equal(supervisor.connection.port, 43101);

  children[1].emit("exit", 1, null);
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(launches.length, 2);
  assert.equal(fatalErrors.length, 1);
  assert.match(fatalErrors[0].message, /one permitted restart/);
});

test("does not restart during intentional shutdown", async () => {
  const { supervisor, children, launches, killed } = createSupervisor();
  await supervisor.start();
  await supervisor.stop();
  children[0].emit("exit", 0, null);
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(launches.length, 1);
  assert.equal(killed.length, 1);
  assert.equal(supervisor.connection, null);
});
