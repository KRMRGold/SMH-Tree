import { randomBytes } from "node:crypto";
import { spawn as nodeSpawn } from "node:child_process";
import { createServer } from "node:net";

const delay = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

export async function findFreeLoopbackPort() {
  const server = createServer();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });

  const address = server.address();
  if (!address || typeof address === "string") {
    await new Promise((resolve) => server.close(resolve));
    throw new Error("Could not determine an available loopback port.");
  }

  const { port } = address;
  await new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
  return port;
}

async function terminateProcessTree(child, platform, spawnProcess) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;

  if (platform === "win32") {
    if (child.pid == null) return;
    await new Promise((resolve) => {
      const killer = spawnProcess(
        "taskkill",
        ["/pid", String(child.pid), "/T", "/F"],
        { windowsHide: true, stdio: "ignore" },
      );
      killer.once("error", resolve);
      killer.once("close", resolve);
    });
    return;
  }

  child.kill("SIGTERM");
  await Promise.race([
    new Promise((resolve) => child.once("exit", resolve)),
    delay(2500),
  ]);
  if (child.exitCode === null && child.signalCode === null) {
    child.kill("SIGKILL");
  }
}

export class BackendSupervisor {
  constructor({
    repoRoot,
    backendDir,
    dataDir,
    command = process.platform === "win32" ? "uv.exe" : "uv",
    spawnProcess = nodeSpawn,
    fetchImpl = globalThis.fetch,
    platform = process.platform,
    tokenFactory = () => randomBytes(32).toString("hex"),
    portFactory = findFreeLoopbackPort,
    argsFactory = ({ backendDir, port }) => [
      "run", "--project", backendDir, "python", "-m", "cogplat",
      "--host", "127.0.0.1", "--port", String(port),
    ],
    sleep = delay,
    startupTimeoutMs = 20_000,
    pollIntervalMs = 200,
    killTree = terminateProcessTree,
    onReady = () => {},
    onFatal = () => {},
  }) {
    if (!repoRoot || !backendDir || !dataDir) {
      throw new Error("repoRoot, backendDir, and dataDir are required.");
    }
    this.repoRoot = repoRoot;
    this.backendDir = backendDir;
    this.dataDir = dataDir;
    this.command = command;
    this.spawnProcess = spawnProcess;
    this.fetchImpl = fetchImpl;
    this.platform = platform;
    this.tokenFactory = tokenFactory;
    this.portFactory = portFactory;
    this.argsFactory = argsFactory;
    this.sleep = sleep;
    this.startupTimeoutMs = startupTimeoutMs;
    this.pollIntervalMs = pollIntervalMs;
    this.killTree = killTree;
    this.onReady = onReady;
    this.onFatal = onFatal;
    this.child = null;
    this.readyChild = null;
    this.connection = null;
    this.restartCount = 0;
    this.stopping = false;
  }

  async start() {
    if (this.connection) return this.connection;
    this.stopping = false;
    this.restartCount = 0;
    return this.#launch();
  }

  async #launch() {
    const port = await this.portFactory();
    if (this.stopping) {
      throw new Error("Backend supervisor stopped before process launch.");
    }
    const token = this.tokenFactory();
    if (!/^[a-f0-9]{64}$/i.test(token)) {
      throw new Error("The backend token factory must return 32 random bytes as hex.");
    }

    const args = this.argsFactory({ backendDir: this.backendDir, port });
    const child = this.spawnProcess(this.command, args, {
      cwd: this.repoRoot,
      env: {
        ...process.env,
        COGPLAT_API_TOKEN: token,
        COGPLAT_DATA_DIR: this.dataDir,
      },
      windowsHide: true,
      stdio: "ignore",
    });
    this.child = child;

    let exitInfo = null;
    child.once("exit", (code, signal) => {
      exitInfo = { code, signal };
      if (this.child === child) this.child = null;
      if (this.connection?.port === port) this.connection = null;
      if (this.readyChild === child) {
        this.readyChild = null;
        void this.#handleUnexpectedExit(code, signal);
      }
    });
    child.once("error", (error) => {
      exitInfo = { error };
      if (this.child === child) this.child = null;
    });

    const baseUrl = `http://127.0.0.1:${port}`;
    const deadline = Date.now() + this.startupTimeoutMs;
    while (Date.now() < deadline) {
      if (exitInfo) {
        throw new Error(
          `Backend process exited before becoming ready: ${exitInfo.error?.message ?? JSON.stringify(exitInfo)}`,
        );
      }
      try {
        const response = await this.fetchImpl(`${baseUrl}/v1/health`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: AbortSignal.timeout(1000),
        });
        if (exitInfo) {
          throw new Error("Backend process exited during its health check.");
        }
        if (response.ok) {
          if (this.stopping) {
            await this.killTree(child, this.platform, this.spawnProcess);
            if (this.child === child) this.child = null;
            throw new Error("Backend supervisor stopped during startup.");
          }
          const connection = { baseUrl, port, token };
          this.connection = connection;
          this.readyChild = child;
          this.onReady(connection);
          return connection;
        }
      } catch (error) {
        if (exitInfo) throw error;
      }
      await this.sleep(this.pollIntervalMs);
    }

    await this.killTree(child, this.platform, this.spawnProcess);
    if (this.child === child) this.child = null;
    throw new Error(`Backend did not become ready within ${this.startupTimeoutMs} ms.`);
  }

  async #handleUnexpectedExit(code, signal) {
    if (this.stopping) return;
    if (this.restartCount >= 1) {
      this.onFatal(
        new Error(`Backend exited after its one permitted restart (code=${code}, signal=${signal}).`),
      );
      return;
    }

    this.restartCount += 1;
    try {
      await this.#launch();
    } catch (error) {
      this.onFatal(error);
    }
  }

  async stop() {
    this.stopping = true;
    this.connection = null;
    this.readyChild = null;
    const child = this.child;
    this.child = null;
    if (child) await this.killTree(child, this.platform, this.spawnProcess);
  }
}
