#!/usr/bin/env node

import { createHash } from "node:crypto";
import { createWriteStream } from "node:fs";
import {
  mkdir,
  open,
  readFile,
  stat,
  writeFile,
} from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";

const DEFAULT_CODEX_HOME = path.join(process.env.HOME ?? "", ".codex");
const DEFAULT_MAX_TAIL_BYTES = 64 * 1024 * 1024;
const DEFAULT_MAX_COMPLETION_CHARS = 64 * 1024;
const MAX_RECORDS_PER_NOTE = 50;

function usage() {
  console.error(
    "Usage: codex-subagent-salvage.mjs --out ABSOLUTE_DIR " +
      "[--codex-home ABSOLUTE_DIR] [--max-tail-mib N]",
  );
}

function parseArgs(argv) {
  const args = {
    codexHome: DEFAULT_CODEX_HOME,
    maxTailBytes: DEFAULT_MAX_TAIL_BYTES,
    out: null,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--out") {
      args.out = argv[++i];
    } else if (arg === "--codex-home") {
      args.codexHome = argv[++i];
    } else if (arg === "--max-tail-mib") {
      args.maxTailBytes = Number(argv[++i]) * 1024 * 1024;
    } else if (arg === "--help" || arg === "-h") {
      usage();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (!args.out || !path.isAbsolute(args.out)) {
    throw new Error("--out must be an absolute directory");
  }
  if (!path.isAbsolute(args.codexHome)) {
    throw new Error("--codex-home must be an absolute directory");
  }
  if (!Number.isFinite(args.maxTailBytes) || args.maxTailBytes <= 0) {
    throw new Error("--max-tail-mib must be a positive number");
  }
  return args;
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function normalizeText(value) {
  return String(value ?? "").replace(/\r\n/g, "\n").trim();
}

function sqliteJson(database, query) {
  const result = spawnSync("sqlite3", ["-json", database, query], {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  if (result.status !== 0) {
    throw new Error(`sqlite3 failed: ${result.stderr || result.stdout}`);
  }
  return JSON.parse(result.stdout || "[]");
}

function projectSlug(cwd) {
  const base = path.basename(cwd || "unknown").toLowerCase();
  return base.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "unknown";
}

function payloadMessage(record) {
  const payload = record?.payload;
  if (!payload || typeof payload !== "object") return "";
  return normalizeText(
    payload.last_agent_message ?? payload.message ?? payload.text ?? "",
  );
}

function classifyLine(line) {
  if (!line.includes('"type":"event_msg"')) return null;
  if (
    !line.includes('"type":"task_complete"') &&
    !line.includes('"type":"turn_aborted"') &&
    !line.includes('"type":"agent_message"')
  ) {
    return null;
  }

  let record;
  try {
    record = JSON.parse(line);
  } catch {
    return null;
  }
  if (record.type !== "event_msg") return null;

  const kind = record.payload?.type;
  if (!["task_complete", "turn_aborted", "agent_message"].includes(kind)) {
    return null;
  }
  return {
    kind,
    message: payloadMessage(record),
    timestamp: record.timestamp ?? null,
    turnId: record.payload?.turn_id ?? null,
  };
}

async function extractTailOutcome(filePath, maxTailBytes) {
  const fileStat = await stat(filePath);
  const handle = await open(filePath, "r");
  const chunkBytes = 1024 * 1024;
  let position = fileStat.size;
  let scannedBytes = 0;
  let carry = Buffer.alloc(0);
  let fallbackAgentMessage = null;
  let aborted = null;

  try {
    while (position > 0 && scannedBytes < maxTailBytes) {
      const bytesToRead = Math.min(
        chunkBytes,
        position,
        maxTailBytes - scannedBytes,
      );
      position -= bytesToRead;
      scannedBytes += bytesToRead;

      const chunk = Buffer.allocUnsafe(bytesToRead);
      await handle.read(chunk, 0, bytesToRead, position);
      const combined = Buffer.concat([chunk, carry]);
      const lines = combined.toString("utf8").split("\n");
      carry = Buffer.from(lines.shift() ?? "", "utf8");

      for (let i = lines.length - 1; i >= 0; i -= 1) {
        const outcome = classifyLine(lines[i]);
        if (!outcome) continue;
        if (outcome.kind === "task_complete") {
          return {
            ...outcome,
            fileSize: fileStat.size,
            fileMtimeMs: fileStat.mtimeMs,
            scannedBytes,
            extraction: "task_complete",
          };
        }
        if (outcome.kind === "turn_aborted" && !aborted) aborted = outcome;
        if (outcome.kind === "agent_message" && outcome.message && !fallbackAgentMessage) {
          fallbackAgentMessage = outcome;
        }
      }
    }

    if (position === 0 && carry.length > 0) {
      const outcome = classifyLine(carry.toString("utf8"));
      if (outcome?.kind === "task_complete") {
        return {
          ...outcome,
          fileSize: fileStat.size,
          fileMtimeMs: fileStat.mtimeMs,
          scannedBytes,
          extraction: "task_complete",
        };
      }
    }
  } finally {
    await handle.close();
  }

  const outcome = aborted ?? fallbackAgentMessage;
  return {
    kind: outcome?.kind ?? "missing",
    message: outcome?.message ?? "",
    timestamp: outcome?.timestamp ?? null,
    turnId: outcome?.turnId ?? null,
    fileSize: fileStat.size,
    fileMtimeMs: fileStat.mtimeMs,
    scannedBytes,
    extraction: outcome ? `fallback_${outcome.kind}` : "missing",
  };
}

function buildMarkdown(slug, records, generatedAt, part, totalParts) {
  const totalBytes = records.reduce((sum, record) => sum + record.file_size, 0);
  const complete = records.filter((record) => record.outcome_kind === "task_complete").length;
  const lines = [
    "---",
    `title: Codex legacy subagent salvage ${slug} ${generatedAt.slice(0, 10)} part ${part}`,
    "type: research",
    "status: temporary",
    "temporary: true",
    `source_generated_at: '${generatedAt}'`,
    "tags:",
    "- codex-history-salvage",
    `- ${slug}`,
    "---",
    "",
    `# Codex legacy subagent salvage — ${slug} — part ${part}/${totalParts}`,
    "",
    "> Temporary recovery ledger. Promote successful durable facts into canonical project notes, then reduce this note to a pointer. Raw duplicated parent context and tool traces were intentionally excluded.",
    "",
    `- Candidate child tasks: ${records.length}`,
    `- Child completions captured: ${complete}`,
    `- Original rollout bytes represented: ${totalBytes}`,
    "",
  ];

  for (const record of records) {
    lines.push(
      `## ${record.agent_path || "unnamed-agent"} — ${record.thread_id}`,
      "",
      `- Parent task: \`${record.parent_thread_id || "unknown"}\``,
      `- Working directory: \`${record.cwd || "unknown"}\``,
      `- Created: ${record.created_at ?? "unknown"}`,
      `- Updated: ${record.updated_at ?? "unknown"}`,
      `- Outcome: ${record.outcome_kind} (${record.extraction})`,
      `- Original rollout: ${record.file_size} bytes`,
      `- Completion SHA-256: \`${record.completion_sha256 || "none"}\``,
      "",
      "### Child-local completion",
      "",
      record.completion || "_No recoverable child completion was found in the configured tail window._",
      "",
    );
  }
  return `${lines.join("\n")}\n`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const stateDb = path.join(args.codexHome, "state_5.sqlite");
  const generatedAt = new Date().toISOString();
  await mkdir(args.out, { recursive: false });

  const query = `
    SELECT
      t.id,
      t.rollout_path,
      t.cwd,
      t.title,
      COALESCE(t.agent_path, json_extract(t.source, '$.subagent.thread_spawn.agent_path')) AS agent_path,
      datetime(t.created_at, 'unixepoch') AS created_at,
      datetime(t.updated_at, 'unixepoch') AS updated_at,
      json_extract(t.source, '$.subagent.thread_spawn.parent_thread_id') AS parent_thread_id,
      json_extract(t.source, '$.subagent.thread_spawn.depth') AS depth,
      p.rollout_path AS parent_rollout_path,
      p.title AS parent_title,
      p.history_mode AS parent_history_mode
    FROM threads t
    LEFT JOIN threads p
      ON p.id = json_extract(t.source, '$.subagent.thread_spawn.parent_thread_id')
    WHERE t.history_mode = 'legacy'
      AND json_valid(t.source)
      AND json_type(t.source, '$.subagent') IS NOT NULL
    ORDER BY t.created_at, t.id;
  `;
  const candidates = sqliteJson(stateDb, query);
  const manifestPath = path.join(args.out, "inventory.jsonl");
  const manifest = createWriteStream(manifestPath, { flags: "wx" });
  const grouped = new Map();
  const records = [];

  let index = 0;
  for (const candidate of candidates) {
    index += 1;
    let outcome;
    try {
      outcome = await extractTailOutcome(candidate.rollout_path, args.maxTailBytes);
    } catch (error) {
      outcome = {
        kind: "read_error",
        message: "",
        timestamp: null,
        turnId: null,
        fileSize: 0,
        fileMtimeMs: null,
        scannedBytes: 0,
        extraction: `error:${error.message}`,
      };
    }

    const fullCompletion = normalizeText(outcome.message);
    const completion = fullCompletion.slice(0, DEFAULT_MAX_COMPLETION_CHARS);
    const slug = projectSlug(candidate.cwd);
    const record = {
      thread_id: candidate.id,
      parent_thread_id: candidate.parent_thread_id ?? null,
      depth: candidate.depth ?? null,
      agent_path: candidate.agent_path ?? null,
      cwd: candidate.cwd ?? null,
      project_slug: slug,
      title: candidate.title ?? null,
      parent_title: candidate.parent_title ?? null,
      parent_history_mode: candidate.parent_history_mode ?? null,
      rollout_path: candidate.rollout_path,
      parent_rollout_path: candidate.parent_rollout_path ?? null,
      created_at: candidate.created_at ?? null,
      updated_at: candidate.updated_at ?? null,
      file_size: outcome.fileSize,
      file_mtime_ms: outcome.fileMtimeMs,
      tail_scanned_bytes: outcome.scannedBytes,
      outcome_kind: outcome.kind,
      extraction: outcome.extraction,
      outcome_timestamp: outcome.timestamp,
      outcome_turn_id: outcome.turnId,
      completion,
      completion_truncated: completion.length !== fullCompletion.length,
      completion_sha256: fullCompletion ? sha256(fullCompletion) : null,
    };

    records.push(record);
    if (!grouped.has(slug)) grouped.set(slug, []);
    grouped.get(slug).push(record);
    manifest.write(`${JSON.stringify(record)}\n`);

    if (index % 25 === 0 || index === candidates.length) {
      console.error(`Extracted ${index}/${candidates.length} legacy subagent rollouts`);
    }
  }

  await new Promise((resolve, reject) => {
    manifest.on("error", reject);
    manifest.end(resolve);
  });

  const projectsDir = path.join(args.out, "projects");
  await mkdir(projectsDir);
  for (const [slug, projectRecords] of grouped) {
    const totalParts = Math.ceil(projectRecords.length / MAX_RECORDS_PER_NOTE);
    for (let part = 1; part <= totalParts; part += 1) {
      const partRecords = projectRecords.slice(
        (part - 1) * MAX_RECORDS_PER_NOTE,
        part * MAX_RECORDS_PER_NOTE,
      );
      await writeFile(
        path.join(projectsDir, `${slug}-part-${String(part).padStart(2, "0")}.md`),
        buildMarkdown(slug, partRecords, generatedAt, part, totalParts),
        { flag: "wx" },
      );
    }
  }

  const summary = {
    schema_version: 1,
    generated_at: generatedAt,
    codex_home: args.codexHome,
    state_db: stateDb,
    candidate_threads: records.length,
    represented_bytes: records.reduce((sum, record) => sum + record.file_size, 0),
    completion_records: records.filter((record) => record.outcome_kind === "task_complete").length,
    fallback_records: records.filter((record) => record.extraction.startsWith("fallback_")).length,
    missing_records: records.filter((record) => record.outcome_kind === "missing").length,
    read_errors: records.filter((record) => record.outcome_kind === "read_error").length,
    truncated_completions: records.filter((record) => record.completion_truncated).length,
    projects: Object.fromEntries(
      [...grouped.entries()].map(([slug, projectRecords]) => [
        slug,
        {
          threads: projectRecords.length,
          bytes: projectRecords.reduce((sum, record) => sum + record.file_size, 0),
          completions: projectRecords.filter((record) => record.outcome_kind === "task_complete").length,
        },
      ]),
    ),
    deletion_ready: false,
    deletion_gate: "Engram write/read receipts and durable-fact promotion are still required.",
  };
  await writeFile(
    path.join(args.out, "summary.json"),
    `${JSON.stringify(summary, null, 2)}\n`,
    { flag: "wx" },
  );
  await writeFile(
    path.join(args.out, "SHA256SUMS"),
    [
      `${sha256(await readFile(manifestPath))}  inventory.jsonl`,
      `${sha256(JSON.stringify(summary))}  summary-object.json`,
    ].join("\n") + "\n",
    { flag: "wx" },
  );

  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
