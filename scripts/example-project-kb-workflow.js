// Reference implementation for /engram:scan — a DOCUMENTATION workflow (not a bug audit).
// HARDENED design (proven on a 41-agent / 4M-token run): chunked pacing + retries +
// fallback work-list + delimited-markdown output (NOT StructuredOutput).
//
// Run via the Workflow tool with args, e.g.:
//   Workflow({ scriptPath: "<this file>", args: {
//     projectRoot: "/abs/path/to/repo",
//     projectName: "my-app",
//     depth: "exhaustive",                 // "overview" | "map" | "exhaustive"
//     auditFile: "/abs/path/audit.json",   // optional: prior audit/notes to mine
//     fallback: { systems:[...], screens:[...], modules:[...] } // optional safety net
//   }})
// Returns { profileText, docTexts[], criticText, ... } — each text channel contains
// ===ENGRAM-NOTE=== ... ===END-NOTE=== blocks. The /engram:scan skill PARSES those blocks
// and writes the notes into ~/Engram/projects/<name>/{product,systems,screens,architecture}.
//
// WHY delimited text and not a schema: a schema with a big "write a whole doc" field makes
// agents emit prose instead of calling StructuredOutput (they fail "without calling the tool").
// Returning markdown is what models do naturally, is lighter on tokens, and can't hit that failure.

export const meta = {
  name: 'project-knowledge-base',
  description: 'Survey a project and produce a comprehensive KB (product/PM + systems + surfaces + architecture) as delimited note blocks — rate-limit hardened',
  phases: [
    { title: 'Survey', detail: 'PM/product profile + systems/surfaces/modules work-list (with fallback)' },
    { title: 'Document', detail: 'Sequential chunks of doc agents → delimited markdown notes' },
    { title: 'Review', detail: 'Completeness critic drafts the missing notes' },
  ],
}

const ROOT = (args && args.projectRoot) || '.'
const NAME = (args && args.projectName) || 'project'
const DEPTH = (args && args.depth) || 'exhaustive'
const AUDIT = args && args.auditFile ? String(args.auditFile) : null
const CHUNK = 6 // keep concurrency gentle so a server-side rate limit doesn't sink the run
const CAP = DEPTH === 'overview' ? { sys: 8, scr: 8, mod: 6 } : DEPTH === 'map' ? { sys: 12, scr: 12, mod: 6 } : { sys: 16, scr: 20, mod: 8 }

const CONTEXT = `You are DOCUMENTING the project at ${ROOT} to build a COMPREHENSIVE, future-developer-and-PM-facing knowledge base — NOT a bug audit. Capture what someone needs to work on it: what it is, how it works, where things live, why decisions were made.
FIRST understand the project type (README, manifests, build files, top-level dirs) and ADAPT vocabulary to it (web → pages/routes/services; backend → endpoints/jobs/schemas; library → modules/APIs; CLI → commands; mobile → screens/systems). Read the ACTUAL code.${AUDIT ? `\nA prior audit/notes file is at ${AUDIT} — mine it for entry points + facts, but verify against current code.` : ''}`

const NOTE_FORMAT = `OUTPUT FORMAT — return your note(s) as PLAIN TEXT, each wrapped EXACTLY like this (no code fences, output nothing else):

===ENGRAM-NOTE===
folder: projects/${NAME}/systems
title: <concise specific title>
tags: tag1, tag2
---BODY---
<note body for someone who has never seen the project: readable PROSE plus basic-memory structured lines — observations "- [category] fact" (categories: product, business, fact, arch, flow, file, data, gotcha, decision, status, convention) and relations "- relation_type [[Other Note Title]]" (uses | part_of | relates_to | implements | depends_on | supersedes). Cite concrete file paths; cross-link to sibling notes.>
===END-NOTE===

One block per note. "folder" MUST be one of: projects/${NAME}/product, projects/${NAME}/systems, projects/${NAME}/screens, projects/${NAME}/architecture, or global/<domain> (a reusable engineering pattern). Keep [[link]] targets close to the real sibling titles. Long, detailed notes are good.`

async function withRetry(fn, tries) {
  let last
  for (let i = 0; i < tries; i++) {
    try { const r = await fn(); if (r) return r } catch (e) { last = String(e).slice(0, 100) }
    if (i < tries - 1) log(`  retry ${i + 1}/${tries - 1} after: ${last || 'empty result'}`)
  }
  return null
}

const INVENTORY_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['systems', 'screens', 'modules'],
  properties: {
    systems: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['name', 'oneLiner'], properties: { name: { type: 'string' }, oneLiner: { type: 'string' }, keyFiles: { type: 'array', items: { type: 'string' } } } } },
    screens: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['name', 'oneLiner'], properties: { name: { type: 'string' }, platform: { type: 'string' }, oneLiner: { type: 'string' }, keyFiles: { type: 'array', items: { type: 'string' } } } } },
    modules: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['name'], properties: { name: { type: 'string' }, keyDirs: { type: 'array', items: { type: 'string' } } } } },
    dataModel: { type: 'object', additionalProperties: false, properties: { tables: { type: 'array', items: { type: 'string' } }, collections: { type: 'array', items: { type: 'string' } }, settingsKeys: { type: 'array', items: { type: 'string' } } } },
  },
}
const FALLBACK = (args && args.fallback) || { systems: [], screens: [], modules: [], dataModel: {} }

// ---------- Phase 1: SURVEY ----------
phase('Survey')
const inventory = (await withRetry(() => agent(
  `${CONTEXT}\n\nTASK: Produce the documentation WORK-LIST by reading the code${AUDIT ? ' + audit data' : ''}. Enumerate systems (major subsystems), screens/surfaces (major user-facing entry points — adapt the term to the project type), modules (top-level code modules), and dataModel (tables/collections/schemas + key config), each with real key files. ~${CAP.sys} systems, ~${CAP.scr} surfaces. Group trivial sub-units under their parent.`,
  { phase: 'Survey', label: 'inventory', schema: INVENTORY_SCHEMA }
), 4)) || (log('inventory unavailable → using fallback work-list'), FALLBACK)

const profileText = await withRetry(() => agent(
  `${CONTEXT}\n\nTASK: Produce the PROJECT-MANAGER / PRODUCT layer. Write SEPARATE notes (folder projects/${NAME}/product, or projects/${NAME}/architecture where technical) for: project overview & elevator pitch + current version/status; monetization / business model (if any); release & versioning + contribution process; external systems & infrastructure; roadmap + disabled/deferred work; team & process/conventions. Be concrete and current.\n\n${NOTE_FORMAT}`,
  { phase: 'Survey', label: 'pm-product-profile' }
), 3) || ''

const systems = (inventory.systems || []).slice(0, CAP.sys).map((s) => ({ ...s, kind: 'system' }))
const screens = (inventory.screens || []).slice(0, CAP.scr).map((s) => ({ ...s, kind: 'screen' }))
const modules = (inventory.modules || []).slice(0, CAP.mod).map((s) => ({ ...s, kind: 'module' }))
const items = [...modules, ...systems, ...screens]
const dataModelBlob = JSON.stringify(inventory.dataModel || {})
log(`work-list: ${modules.length} modules, ${systems.length} systems, ${screens.length} surfaces → ${items.length} doc agents (chunks of ${CHUNK}, depth=${DEPTH})`)

const kindGuide = {
  system: `Document the SYSTEM end-to-end: what it is (PRODUCT purpose + technical), full flow across the stack, data it touches, key files with paths, flows + edge cases, conventions & gotchas, status. Folder: projects/${NAME}/systems.`,
  screen: `Document the SURFACE/SCREEN/FLOW: purpose, what the user sees and can do, structure/sub-units, the data/state it binds, navigation in/out, files (per platform if relevant) with paths, any divergence. Folder: projects/${NAME}/screens.`,
  module: `Document the MODULE: responsibility, directory layout, key components, the boundaries/interfaces it exposes or consumes. Folder: projects/${NAME}/architecture.`,
}
const docPrompt = (it) => `${CONTEXT}\n\nTASK: Write COMPREHENSIVE documentation note(s) for this ${it.kind}: "${it.name}".\nOne-liner: ${it.oneLiner || '(derive it)'}\nStart from these key files (verify + read, then expand): ${(it.keyFiles || it.keyDirs || []).join(', ') || '(discover them)'}\n\n${kindGuide[it.kind]}\nData model: ${dataModelBlob}\nEmit 1-3 notes. ${NOTE_FORMAT}`

// ---------- Phase 2: DOCUMENT (sequential chunks, retry failures) ----------
phase('Document')
const docTexts = []
let failed = []
for (let i = 0; i < items.length; i += CHUNK) {
  const batch = items.slice(i, i + CHUNK)
  const res = await parallel(batch.map((it) => () => agent(docPrompt(it), { phase: 'Document', label: `doc:${it.kind}:${it.name}`.slice(0, 55) })))
  res.forEach((r, j) => { if (r) docTexts.push(r); else failed.push(batch[j]) })
  log(`batch ${Math.floor(i / CHUNK) + 1}/${Math.ceil(items.length / CHUNK)}: ${res.filter(Boolean).length}/${batch.length} ok (fails so far: ${failed.length})`)
}
if (failed.length) {
  log(`retrying ${failed.length} failed doc agents`)
  const retryItems = failed; failed = []
  for (let i = 0; i < retryItems.length; i += CHUNK) {
    const batch = retryItems.slice(i, i + CHUNK)
    const res = await parallel(batch.map((it) => () => agent(docPrompt(it), { phase: 'Document', label: `retry:${it.kind}:${it.name}`.slice(0, 55) })))
    res.forEach((r, j) => { if (r) docTexts.push(r); else failed.push(batch[j]) })
  }
}
log(`documented ${docTexts.length} agent outputs; ${failed.length} still failed`)

// ---------- Phase 3: REVIEW (completeness critic) ----------
phase('Review')
const criticText = await withRetry(() => agent(
  `${CONTEXT}\n\nYou are the COMPLETENESS CRITIC — make this KB EXHAUSTIVE. Intended coverage: systems=${JSON.stringify(systems.map((s) => s.name))} screens=${JSON.stringify(screens.map((s) => s.name))} modules=${JSON.stringify(modules.map((s) => s.name))} dataModel=${dataModelBlob}.\nThese topics may have failed and need writing: ${JSON.stringify(failed.map((f) => f.name))}.\nRead the repo${AUDIT ? ' + audit data' : ''}. Find what's MISSING or thin for a future developer/PM (an uncovered system/surface/integration/data area/PM aspect/convention/runbook). DRAFT the missing notes in full now. Be exhaustive.\n\n${NOTE_FORMAT}`,
  { phase: 'Review', label: 'completeness-critic' }
), 3) || ''

return { usedFallback: inventory === FALLBACK, profileText, docTexts, criticText, failedTopics: failed.map((f) => f.name), counts: { items: items.length, docOutputs: docTexts.length } }
