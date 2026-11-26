import assert from "node:assert/strict";
import { once } from "node:events";
import { mkdtemp, rm, stat } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import { _electron as electron } from "playwright";

const executablePath = path.resolve(
  process.env.SMH_TREE_PACKAGED_EXE ?? "out/SMH-Tree-win32-x64/SMH-Tree.exe",
);
const claimText = "The Cedar Lantern launch is scheduled for Friday.";

function fakeOllama() {
  return createServer(async (request, response) => {
    if (request.url === "/api/tags") {
      response.setHeader("Content-Type", "application/json");
      response.end(JSON.stringify({ models: [{ name: "test-model" }] }));
    } else if (request.url === "/api/chat" && request.method === "POST") {
      const chunks = [];
      for await (const chunk of request) chunks.push(chunk);
      const body = JSON.parse(Buffer.concat(chunks));
      const content = body.format === "json"
        ? JSON.stringify({
          claims: [{
            claim_type: "factual",
            text: claimText,
            evidence_excerpt: claimText,
          }],
        })
        : "Launch note received.";
      response.setHeader("Content-Type", "application/x-ndjson");
      response.end(JSON.stringify({ message: { content }, done: true }) + "\n");
    } else {
      response.writeHead(404).end();
    }
  });
}

test("packaged app chats, extracts a claim, and reopens it without Python on PATH", { timeout: 90_000 }, async () => {
  const profile = await mkdtemp(path.join(tmpdir(), "smh-tree-m10-"));
  const provider = fakeOllama();
  let app;

  try {
    provider.listen(0, "127.0.0.1");
    await once(provider, "listening");
    const env = Object.fromEntries(Object.entries(process.env).filter(([name]) =>
      !/^(?:PATH|PYTHONHOME|PYTHONPATH|VIRTUAL_ENV|ELECTRON_RUN_AS_NODE)$/i.test(name)
    ));
    env.Path = path.join(process.env.SystemRoot ?? "C:\\Windows", "System32");
    env.COGPLAT_OLLAMA_BASE_URL = `http://127.0.0.1:${provider.address().port}`;
    env.COGPLAT_WORKFLOWS_ENABLED = "true";

    const launch = () => electron.launch({
      executablePath,
      args: [`--user-data-dir=${profile}`],
      cwd: profile,
      env,
      timeout: 30_000,
    });

    app = await launch();
    let page = await app.firstWindow();
    const backendUrl = await page.evaluate(() => window.cog.getApiBase());
    assert.equal(new URL(backendUrl).hostname, "127.0.0.1");
    assert.equal((await fetch(backendUrl + "/v1/health")).status, 401);
    assert.equal(
      path.resolve(await page.evaluate(() => window.cog.getDataDirectory())),
      path.resolve(profile),
    );

    await page.locator("#new-project").click();
    await page.locator("#input-dialog-value").fill("Installer smoke project");
    await page.getByRole("button", { name: "Continue", exact: true }).click();
    await page.locator("#project-select option").filter({ hasText: "Installer smoke project" })
      .waitFor({ state: "attached" });
    await page.locator("#new-conversation").click();
    await page.locator("#input-dialog-value").fill("Installer smoke conversation");
    await page.getByRole("button", { name: "Continue", exact: true }).click();
    await page.locator("#ollama-model option[value='test-model']").waitFor({ state: "attached" });
    await page.locator("#message-input").fill(claimText);
    await page.locator("#send-button").click();
    await page.getByText("Launch note received.", { exact: true }).waitFor();
    await page.locator(".message.user").getByRole("button", { name: "Extract claims" }).click();
    await page.locator("#extraction-dialog").getByRole("button", { name: "Extract claims" }).click();
    await page.getByRole("button", { name: "Review claims" }).click();
    await page.locator("#claim-detail").getByRole("heading", { name: claimText, exact: true }).waitFor();
    await page.locator("#claim-detail").getByText("default: proposed", { exact: true }).waitFor();
    await page.locator("#claim-detail").getByText(claimText, { exact: true }).last().waitFor();
    await stat(path.join(profile, "app.db"));

    await app.close();
    app = null;
    await assert.rejects(fetch(backendUrl + "/v1/health", { signal: AbortSignal.timeout(2000) }));

    app = await launch();
    page = await app.firstWindow();
    const project = page.locator("#project-select option").filter({ hasText: "Installer smoke project" });
    await project.waitFor({ state: "attached" });
    await page.locator("#project-select").selectOption(await project.getAttribute("value"));
    await page.getByRole("button", { name: "Claims", exact: true }).click();
    await page.locator("#claims-list").getByRole("button", { name: claimText, exact: true }).waitFor();
  } finally {
    if (app) await app.close();
    provider.closeAllConnections();
    await new Promise((resolve) => provider.close(resolve));
    await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  }
});
