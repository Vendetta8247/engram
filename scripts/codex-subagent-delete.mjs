#!/usr/bin/env node

import { createHash } from "node:crypto";
import { createWriteStream } from "node:fs";
import { access, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { spawn, spawnSync } from "node:child_process";
import readline from "node:readline";

const REQUIRED_ACK = "YES_DELETE_VERIFIED_LEGACY_SUBAGENTS";

function parseArgs(argv) {
  const args = {
    acknowledge: null,
    backup: null,
    codexHome: path.join(process.env.HOME ?? "", ".codex"),
    confirmSha256: null,
    manifest: null,
    receipt: null,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--manifest") args.manifest = argv[++i];
    else if (arg === "--confirm-sha256") args.confirmSha256 = argv[++i];
    else if (arg === "--receipt") args.receipt = argv[++i];
    else if (arg === "--engram-backup") args.backup = argv[++i];
    else if (arg === "--codex-home") args.codexHome = argv[++i];
    else if (arg === "--acknowledge-permanent-delete") args.acknowledge = argv[++i];
    else throw new Error(`Unknown argument: ${arg}`);
  }
  for (const key of ["manifest", "receipt", "backup", "codexHome"]) {
    if (!args[key] || !path.isAbsolute(args[key])) {
      throw new Error(`--${key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)} must be absolute`);
    }
  }
  if (!/^[a-f0-9]{64}$/.test(args.confirmSha256 ?? "")) {
    throw new Error("--confirm-sha256 must be a lowercase SHA-256 digest");
  }
  if (args.acknowledge !== REQUIRED_ACK) {
    throw new Error(`Permanent deletion requires: --acknowledge-permanent-delete ${REQUIRED_ACK}`);
  }
  return args;
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function run(command, commandArgs, options = {}) {
  const result = spawnSync(command, commandArgs, {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
    ...options,
  });
  if (result.status !== 0) {
    throw new Error(
      `${command} ${commandArgs.join(" ")} failed: ${result.stderr || result.stdout}`,
    );
  }
  return result.stdout;
}

function sqliteJson(database, query) {
  return JSON.parse(run("sqlite3", ["-json", database, query]) || "[]");
}

function quoteSql(value) {
  return `'${String(value).replaceAll("'", "''")}'`;
}

function freeBytes(target) {
  const output = run("df", ["-k", target]).trim().split("\n").at(-1);
  const columns = output.trim().split(/\s+/);
  return Number(columns[3]) * 1024;
}

async function exists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

class AppServerClient {
  constructor(codexHome) {
    this.child = spawn("codex", ["app-server"], {
      env: { ...process.env, CODEX_HOME: codexHome },
      stdio: ["pipe", "pipe", "pipe"],
    });
    this.nextId = 1;
    this.pending = new Map();
    this.deletedNotifications = [];
    this.stderr = "";
    this.child.stderr.on("data", (data) => {
      this.stderr = (this.stderr + data.toString()).slice(-16000);
    });
    const lines = readline.createInterface({ input: this.child.stdout });
    lines.on("line", (line) => {
      let message;
      try {
        message = JSON.parse(line);
      } catch {
        return;
      }
      if (message.method === "thread/deleted") {
        this.deletedNotifications.push(message.params?.threadId ?? null);
      }
      if (message.id == null) return;
      const pending = this.pending.get(message.id);
      if (!pending) return;
      this.pending.delete(message.id);
      clearTimeout(pending.timer);
      if (message.error) pending.reject(new Error(JSON.stringify(message.error)));
      else pending.resolve(message.result);
    });
    this.child.on("exit", (code, signal) => {
      if (code === 0 || signal === "SIGTERM") return;
      const error = new Error(
        `codex app-server exited code=${code} signal=${signal}: ${this.stderr}`,
      );
      for (const pending of this.pending.values()) pending.reject(error);
      this.pending.clear();
    });
  }

  request(method, params, timeoutMs = 30000) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`${method} timed out after ${timeoutMs} ms`));
      }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(`${JSON.stringify({ method, id, params })}\n`);
    });
  }

  notify(method, params) {
    this.child.stdin.write(`${JSON.stringify({ method, params })}\n`);
  }

  close() {
    this.child.kill("SIGTERM");
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const manifestBytes = await readFile(args.manifest);
  const manifestDigest = sha256(manifestBytes);
  if (manifestDigest !== args.confirmSha256) {
    throw new Error(
      `Manifest digest mismatch: expected ${args.confirmSha256}, got ${manifestDigest}`,
    );
  }

  run("shasum", ["-a", "256", "-c", path.join(args.backup, "SHA256SUMS")], {
    cwd: args.backup,
  });
  const backupIntegrity = run("sqlite3", [
    path.join(args.backup, "memory.db"),
    "PRAGMA integrity_check;",
  ]).trim();
  if (backupIntegrity !== "ok") {
    throw new Error(`Engram backup integrity failed: ${backupIntegrity}`);
  }

  const records = manifestBytes
    .toString("utf8")
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
  if (records.length === 0) throw new Error("Manifest contains no records");
  if (records.some((record) => !["task_complete", "turn_aborted"].includes(record.outcome_kind))) {
    throw new Error("Manifest includes an outcome that was neither completed nor explicitly aborted");
  }
  if (records.some((record) => record.completion_truncated)) {
    throw new Error("Manifest contains a truncated completion");
  }

  const stateDb = path.join(args.codexHome, "state_5.sqlite");
  const historyDb = path.join(args.codexHome, "thread_history_1.sqlite");
  const liveRows = sqliteJson(
    stateDb,
    `SELECT id, rollout_path, history_mode, source FROM threads
     WHERE history_mode='legacy'
       AND json_valid(source)
       AND json_type(source, '$.subagent') IS NOT NULL;`,
  );
  const liveById = new Map(liveRows.map((row) => [row.id, row]));
  const manifestIds = new Set(records.map((record) => record.thread_id));
  const unexpectedLive = liveRows.filter((row) => !manifestIds.has(row.id));
  if (unexpectedLive.length > 0) {
    throw new Error(
      `Found ${unexpectedLive.length} live legacy subagent rows absent from the signed manifest`,
    );
  }

  for (const record of records) {
    const live = liveById.get(record.thread_id);
    const fileExists = await exists(record.rollout_path);
    if (!live) {
      if (fileExists) {
        throw new Error(`State row missing but rollout still exists: ${record.thread_id}`);
      }
      continue;
    }
    if (live.rollout_path !== record.rollout_path) {
      throw new Error(`Rollout path changed after salvage: ${record.thread_id}`);
    }
    if (!fileExists) {
      throw new Error(`Rollout disappeared after salvage: ${record.thread_id}`);
    }
    const current = await stat(record.rollout_path);
    if (
      current.size !== record.file_size ||
      Math.abs(current.mtimeMs - record.file_mtime_ms) > 1
    ) {
      throw new Error(`Rollout changed after salvage: ${record.thread_id}`);
    }
  }

  const receiptStream = createWriteStream(args.receipt, { flags: "wx" });
  const startedAt = new Date().toISOString();
  const freeBefore = freeBytes(args.codexHome);
  const client = new AppServerClient(args.codexHome);
  const receipts = [];

  try {
    await client.request("initialize", {
      clientInfo: {
        name: "engram_history_cleanup",
        title: "Engram History Cleanup",
        version: "0.1.0",
      },
    });
    client.notify("initialized", {});
    const loaded = await client.request("thread/loaded/list", {});
    const loadedIds = new Set(loaded?.data ?? loaded?.threadIds ?? []);
    const loadedCandidates = records.filter((record) => loadedIds.has(record.thread_id));
    if (loadedCandidates.length > 0) {
      throw new Error(
        `Refusing to delete ${loadedCandidates.length} currently loaded candidate threads`,
      );
    }

    records.sort((a, b) => (b.depth ?? -1) - (a.depth ?? -1));
    let index = 0;
    for (const record of records) {
      index += 1;
      const live = liveById.get(record.thread_id);
      const receipt = {
        deleted_at: new Date().toISOString(),
        thread_id: record.thread_id,
        parent_thread_id: record.parent_thread_id,
        depth: record.depth,
        agent_path: record.agent_path,
        cwd: record.cwd,
        rollout_path: record.rollout_path,
        bytes: record.file_size,
        completion_sha256: record.completion_sha256,
        outcome_kind: record.outcome_kind,
        status: live ? "pending" : "already_deleted",
      };
      if (live) {
        await client.request("thread/delete", { threadId: record.thread_id }, 60000);
        receipt.status = "deleted";
      }
      receiptStream.write(`${JSON.stringify(receipt)}\n`);
      receipts.push(receipt);
      if (index % 25 === 0 || index === records.length) {
        console.error(`Deleted ${index}/${records.length} verified legacy subagent tasks`);
      }
    }
  } finally {
    client.close();
    await new Promise((resolve, reject) => {
      receiptStream.on("error", reject);
      receiptStream.end(resolve);
    });
  }

  const quotedIds = records.map((record) => quoteSql(record.thread_id)).join(",");
  const remainingState = sqliteJson(
    stateDb,
    `SELECT id FROM threads WHERE id IN (${quotedIds});`,
  );
  const remainingHistory = sqliteJson(
    historyDb,
    `SELECT thread_id, COUNT(*) AS rows FROM (
       SELECT thread_id FROM thread_turns WHERE thread_id IN (${quotedIds})
       UNION ALL SELECT thread_id FROM thread_items WHERE thread_id IN (${quotedIds})
       UNION ALL SELECT thread_id FROM thread_history_projection_state WHERE thread_id IN (${quotedIds})
       UNION ALL SELECT thread_id FROM thread_realtime_items WHERE thread_id IN (${quotedIds})
     ) GROUP BY thread_id;`,
  );
  const remainingFiles = [];
  for (const record of records) {
    if (await exists(record.rollout_path)) remainingFiles.push(record.rollout_path);
  }
  if (remainingState.length || remainingHistory.length || remainingFiles.length) {
    throw new Error(
      `Post-delete residue: state=${remainingState.length} history=${remainingHistory.length} files=${remainingFiles.length}`,
    );
  }

  const stateIntegrity = run("sqlite3", [stateDb, "PRAGMA integrity_check;"]).trim();
  const historyIntegrity = run("sqlite3", [historyDb, "PRAGMA integrity_check;"]).trim();
  const freeAfter = freeBytes(args.codexHome);
  const summary = {
    schema_version: 1,
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    manifest: args.manifest,
    manifest_sha256: manifestDigest,
    engram_backup: args.backup,
    candidates: records.length,
    deleted: receipts.filter((receipt) => receipt.status === "deleted").length,
    already_deleted: receipts.filter((receipt) => receipt.status === "already_deleted").length,
    represented_bytes: records.reduce((sum, record) => sum + record.file_size, 0),
    free_bytes_before: freeBefore,
    free_bytes_after: freeAfter,
    free_bytes_gained: freeAfter - freeBefore,
    remaining_state_rows: remainingState.length,
    remaining_history_rows: remainingHistory.length,
    remaining_files: remainingFiles.length,
    state_integrity: stateIntegrity,
    history_integrity: historyIntegrity,
    receipt_sha256: sha256(await readFile(args.receipt)),
  };
  await writeFile(`${args.receipt}.summary.json`, `${JSON.stringify(summary, null, 2)}\n`, {
    flag: "wx",
  });
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
