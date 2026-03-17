#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const cp = require("child_process");

const packageRoot = path.resolve(__dirname, "..");
const runtimeDir = path.join(packageRoot, ".runtime");
const cliRoot = path.join(packageRoot, "cli");
const requirementsPath = path.join(cliRoot, "requirements.txt");

function runtimePythonPath() {
  return process.platform === "win32"
    ? path.join(runtimeDir, "Scripts", "python.exe")
    : path.join(runtimeDir, "bin", "python");
}

function existingSystemPython() {
  const candidates =
    process.platform === "win32"
      ? [["py", ["-3"]], ["python", []]]
      : [["python3", []], ["python", []]];
  for (const [cmd, baseArgs] of candidates) {
    const result = cp.spawnSync(cmd, [...baseArgs, "--version"], { stdio: "ignore" });
    if (result.status === 0) {
      return { cmd, baseArgs };
    }
  }
  return null;
}

function ensureRuntime() {
  const pythonPath = runtimePythonPath();
  if (fs.existsSync(pythonPath)) {
    return pythonPath;
  }

  const systemPython = existingSystemPython();
  if (!systemPython) {
    console.error("Python 3 was not found. Install Python first, then run redmine again.");
    process.exit(1);
  }

  console.log("Bootstrapping local Python runtime for redmine...");
  fs.mkdirSync(runtimeDir, { recursive: true });

  const createVenv = cp.spawnSync(systemPython.cmd, [...systemPython.baseArgs, "-m", "venv", runtimeDir], {
    stdio: "inherit",
    cwd: packageRoot
  });
  if (createVenv.status !== 0) {
    process.exit(createVenv.status || 1);
  }

  const installDeps = cp.spawnSync(pythonPath, ["-m", "pip", "install", "-r", requirementsPath], {
    stdio: "inherit",
    cwd: packageRoot
  });
  if (installDeps.status !== 0) {
    process.exit(installDeps.status || 1);
  }

  return pythonPath;
}

const pythonPath = ensureRuntime();
const child = cp.spawnSync(pythonPath, ["-m", "redmine_timetable_cli", ...process.argv.slice(2)], {
  stdio: "inherit",
  cwd: cliRoot,
  env: {
    ...process.env,
    PYTHONPATH: cliRoot,
    REDMINE_TIMETABLE_WORKDIR: process.cwd(),
    REDMINE_TIMETABLE_CURRENT_DIR: process.cwd(),
    REDMINE_TIMETABLE_PACKAGE_ROOT: packageRoot
  }
});

process.exit(child.status === null ? 1 : child.status);
