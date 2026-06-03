// Reference implementation for /engram:scan — a DOCUMENTATION workflow (not a bug audit).
// Run via the Workflow tool with args, e.g.:
//   Workflow({ scriptPath: "<this file>", args: {
//     projectRoot: "/abs/path/to/repo",
//     projectName: "my-app",
//     depth: "exhaustive",            // "overview" | "map" | "exhaustive"
//     auditFile: "/abs/path/audit.json" // optional: a prior audit/notes to mine
//   }})
// It returns NOTE specs ({title, folder, tags, markdownBody, relatesTo}); the /engram:scan
// skill then writes them into ~/Engram/projects/<name>/{product,systems,screens,architecture}.
// Adapt freely per project — the agent SHOULD tailor the work-list vocabulary to the project type.

export const meta = {
  name: 'project-knowledge-base',
  description: 'Survey a project and produce a comprehensive knowledge base (product/PM + systems + surfaces + architecture) as Engram note specs',
  phases: [
    { title: 'Survey', detail: 'PM/product profile + systems/surfaces/modules work-list' },
    { title: 'Document', detail: 'One agent per unit → comprehensive note specs' },
    { title: 'Review', detail: 'Completeness critic drafts the missing notes' },
  ],
}

const ROOT = (args && args.projectRoot) || '.'
const NAME = (args && args.projectName) || 'project'
const DEPTH = (args && args.depth) || 'exhaustive'
const AUDIT = args && args.auditFile ? String(args.auditFile) : null
const CAP = DEPTH === 'overview' ? { sys: 8, scr: 8, mod: 6 } : DEPTH === 'map' ? { sys: 12, scr: 12, mod: 6 } : { sys: 16, scr: 20, mod: 8 }

const CONTEXT = `You are DOCUMENTING the project at ${ROOT} to build a COMPREHENSIVE, future-developer-and-PM-facing knowledge base — NOT a bug audit. Capture everything someone would need to work on it effectively: what it is, how it works, where things live, why decisions were made.
FIRST understand the project type (read README, manifests, build files, top-level dirs) and ADAPT your vocabulary to it (web app → pages/routes/services; backend → endpoints/jobs/schemas; library → modules/APIs; CLI → commands; mobile → screens/systems). Read the ACTUAL code/config/docs.${AUDIT ? `\nA prior audit/notes file is available at ${AUDIT} — mine it for entry points and facts, but verify against current code.` : ''}`

const NOTE_CONVENTION = `Return one or more NOTES. Each: title; folder ∈ {"projects/${NAME}/product","projects/${NAME}/systems","projects/${NAME}/screens","projects/${NAME}/architecture","global/<domain>"} (global ONLY for genuinely reusable engineering patterns, domain ∈ a tech area like kmp|ios|android|functions|web|backend|workflow); tags; and markdownBody. The markdownBody must be genuinely informative for someone who has never seen the project: readable PROSE plus basic-memory structured lines — observations "- [category] fact" ([product],[business],[fact],[arch],[flow],[file],[data],[gotcha],[decision],[status],[convention]) and relations "- relation_type [[Other Note Title]]" (uses|part_of|relates_to|implements|depends_on|supersedes). Cite concrete file paths and cross-link to sibling notes. Long notes are fine. Also set relatesTo to the titles you linked.`

const NOTE_ITEM = { type: 'object', additionalProperties: false, required: ['title', 'folder', 'markdownBody'],
  properties: { title: { type: 'string' }, folder: { type: 'string' }, tags: { type: 'array', items: { type: 'string' } }, markdownBody: { type: 'string' }, relatesTo: { type: 'array', items: { type: 'string' } } } }
const NOTES_SCHEMA = { type: 'object', additionalProperties: false, required: ['notes'], properties: { notes: { type: 'array', items: NOTE_ITEM } } }
const UNIT = { type: 'object', additionalProperties: false, required: ['name', 'oneLiner'], properties: { name: { type: 'string' }, platform: { type: 'string' }, oneLiner: { type: 'string' }, keyFiles: { type: 'array', items: { type: 'string' } } } }
const INVENTORY_SCHEMA = { type: 'object', additionalProperties: false, required: ['systems', 'screens', 'modules'],
  properties: { systems: { type: 'array', items: UNIT }, screens: { type: 'array', items: UNIT }, modules: { type: 'array', items: UNIT },
    dataModel: { type: 'object', additionalProperties: false, properties: { tables: { type: 'array', items: { type: 'string' } }, collections: { type: 'array', items: { type: 'string' } }, note: { type: 'string' } } } } }
const GAPS_SCHEMA = { type: 'object', additionalProperties: false, required: ['notes'],
  properties: { missing: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['title', 'why'], properties: { title: { type: 'string' }, folder: { type: 'string' }, why: { type: 'string' }, keyFiles: { type: 'array', items: { type: 'string' } } } } }, notes: { type: 'array', items: NOTE_ITEM } } }

phase('Survey')
const [profile, inventory] = await parallel([
  () => agent(`${CONTEXT}\n\nTASK: Produce the PROJECT-MANAGER / PRODUCT layer as notes (folders projects/${NAME}/product, or projects/${NAME}/architecture where technical). Separate notes for: (1) Project overview & elevator pitch, platforms, current version/status; (2) Monetization / business model (if any); (3) Release & versioning + contribution process; (4) External systems & infrastructure; (5) Roadmap, disabled & deferred work; (6) Team & process/conventions. Be concrete and current.\n\n${NOTE_CONVENTION}`,
    { phase: 'Survey', label: 'pm-product-profile', schema: NOTES_SCHEMA }),
  () => agent(`${CONTEXT}\n\nTASK: Produce the documentation WORK-LIST. Enumerate, with real key files for each: systems (major cross-cutting subsystems), screens (major user-facing surfaces/pages/flows — adapt the term to the project type), modules (top-level code modules/packages), and dataModel (tables/collections/schemas). Aim for ~${CAP.sys} systems and ~${CAP.scr} surfaces; group trivial sub-units under their parent. Be thorough and accurate with key files — this drives the whole KB.`,
    { phase: 'Survey', label: 'inventory', schema: INVENTORY_SCHEMA }),
])

const systems = (inventory && inventory.systems || []).slice(0, CAP.sys).map((s) => ({ ...s, kind: 'system' }))
const screens = (inventory && inventory.screens || []).slice(0, CAP.scr).map((s) => ({ ...s, kind: 'screen' }))
const modules = (inventory && inventory.modules || []).slice(0, CAP.mod).map((s) => ({ ...s, kind: 'module' }))
const items = [...modules, ...systems, ...screens]
const dataModelBlob = JSON.stringify((inventory && inventory.dataModel) || {})
log(`work-list: ${modules.length} modules, ${systems.length} systems, ${screens.length} surfaces → ${items.length} doc agents (depth=${DEPTH})`)

const kindGuide = {
  system: `Document the SYSTEM end-to-end: what it is (PRODUCT purpose + technical), the full flow across the stack, the data it touches, key files with paths, important flows + edge cases, conventions & gotchas, current status. Folder: projects/${NAME}/systems.`,
  screen: `Document the SURFACE/SCREEN/FLOW: purpose, what the user sees and can do, its structure/sub-units, the data/state it binds, navigation in and out, the files (per platform if relevant) with paths, any divergence. Folder: projects/${NAME}/screens.`,
  module: `Document the MODULE: responsibility, directory layout, key components, the boundaries/interfaces it exposes or consumes. Folder: projects/${NAME}/architecture.`,
}
function docPrompt(it) {
  return `${CONTEXT}\n\nTASK: Write COMPREHENSIVE documentation note(s) for this ${it.kind}: "${it.name}".\nOne-liner: ${it.oneLiner || '(derive it)'}\nStart from these key files (verify + read them, then expand): ${(it.keyFiles || []).join(', ') || '(discover them)'}\n\n${kindGuide[it.kind]}\n\nProject data model for reference: ${dataModelBlob}\n\nEmit 1-3 notes as needed. ${NOTE_CONVENTION}`
}

phase('Document')
const docResults = await parallel(items.map((it) => () => agent(docPrompt(it), { phase: 'Document', label: `doc:${it.kind}:${it.name}`.slice(0, 60), schema: NOTES_SCHEMA })))

const produced = []
;(profile && profile.notes || []).forEach((n) => produced.push(n.title))
docResults.filter(Boolean).forEach((r) => (r.notes || []).forEach((n) => produced.push(n.title)))
log(`documented ${produced.length} notes; running completeness critic`)

phase('Review')
const critic = await agent(`${CONTEXT}\n\nYou are the COMPLETENESS CRITIC — the safety net that makes this KB EXHAUSTIVE.\nWork-list intended: systems=${JSON.stringify(systems.map((s) => s.name))} screens=${JSON.stringify(screens.map((s) => s.name))} modules=${JSON.stringify(modules.map((s) => s.name))} dataModel=${dataModelBlob}\nTitles produced: ${JSON.stringify(produced)}\nFind what's MISSING or too thin for a future developer/PM (an uncovered system/surface/integration/data area/PM aspect/convention/runbook, or missing cross-links). For each gap, PREFERABLY draft the missing note now (correct folder, real paths, cross-linked) in "notes"; otherwise list it in "missing" with keyFiles. Be exhaustive.\n\n${NOTE_CONVENTION}`,
  { phase: 'Review', label: 'completeness-critic', schema: GAPS_SCHEMA })

return {
  profileNotes: (profile && profile.notes) || [],
  inventory: inventory || {},
  docNotes: docResults.filter(Boolean).flatMap((r) => r.notes || []),
  criticNotes: (critic && critic.notes) || [],
  criticMissing: (critic && critic.missing) || [],
}
