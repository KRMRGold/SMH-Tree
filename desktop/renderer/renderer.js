const status = document.querySelector("#status");
const indicator = document.querySelector("#indicator");
const version = document.querySelector("#version");

async function connect() {
  try {
    const baseUrl = await window.cog.getApiBase();
    if (!baseUrl) throw new Error("The local backend is unavailable.");

    const result = await window.cog.request("/v1/health");
    if (!result.ok || result.data?.status !== "ok") {
      throw new Error("The local backend did not pass its health check.");
    }

    status.textContent = "Local backend connected";
    indicator.dataset.state = "ready";
    version.textContent = `Backend ${result.data.version} · Schema ${result.data.schema_version}`;
  } catch (error) {
    status.textContent = "Backend connection failed";
    indicator.dataset.state = "error";
    version.textContent = error.message;
  }
}

void connect();
