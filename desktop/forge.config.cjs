const path = require("node:path");
const { existsSync } = require("node:fs");
const { execFile } = require("node:child_process");
const { createRequire } = require("node:module");
const { promisify } = require("node:util");

const backend = path.resolve(__dirname, "../backend");
const sidecar = path.join(backend, "dist", "cogplat");
const setupName = "SMH-Tree-Setup.exe";
const run = promisify(execFile);

module.exports = {
  packagerConfig: {
    asar: true,
    executableName: "SMH-Tree",
    extraResource: [sidecar],
    ignore: [/^\/(?:tests|e2e|scripts)(?:\/|$)/],
  },
  hooks: {
    prePackage: async (_config, platform, arch) => {
      if (platform !== "win32" || arch !== "x64") {
        throw new Error("The SMH-Tree installer currently targets Windows x64.");
      }
      if (!existsSync(path.join(sidecar, "cogplat.exe"))) {
        throw new Error("Build the Windows backend first with npm run build:backend.");
      }
    },
    postMake: async (_config, results) => {
      const requireFromMaker = createRequire(require.resolve("@electron-forge/maker-squirrel"));
      const installerTools = path.dirname(requireFromMaker.resolve("electron-winstaller/package.json"));
      for (const { artifacts } of results) {
        const setup = artifacts.find((file) => path.basename(file) === setupName);
        const fullPackage = artifacts.find((file) => file.endsWith("-full.nupkg"));
        if (!setup || !fullPackage) throw new Error("Squirrel did not produce the expected installer files.");
        await run("uv", [
          "run", "--project", backend, "--locked", "--no-sync", "python",
          path.join(__dirname, "scripts", "ensure-squirrel-payload.py"),
          setup, fullPackage, installerTools,
        ], { cwd: __dirname, windowsHide: true });
      }
      return results;
    },
  },
  makers: [
    {
      name: "@electron-forge/maker-squirrel",
      config: {
        name: "SMHTree",
        exe: "SMH-Tree.exe",
        authors: "SMH-Tree contributors",
        setupExe: setupName,
      },
    },
  ],
};
