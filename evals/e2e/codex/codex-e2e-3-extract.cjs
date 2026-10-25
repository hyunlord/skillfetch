#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { isDeepStrictEqual } = require('node:util');
const { extractRun } = require('./codex-e2e-2-extract.cjs');
const REPLICATES = ['r1', 'r2', 'r3'];
const ORACLE_SHA256 = '7db50e73c7dfd6b0b810ba65231fd1475a25a563651310592c88da23795e108c';
const HELP = 'Usage: node codex-e2e-3-extract.cjs --run-root DIR [--r1-dir DIR --r2-dir DIR --r3-dir DIR] [--out FILE]\nOffline only. Defaults: DIR/r1,r2,r3; DIR/observations-e2e3.json. Requires finished manifests and new output paths.\n';
const unique = xs => [...new Set(xs)];
const sha256 = x => crypto.createHash('sha256').update(x).digest('hex');
const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const counts = xs => xs.reduce((out, value) => { const key = String(value); out[key] = (out[key] || 0) + 1; return out; }, {});
const info = file => ({ file, sha256: sha256(fs.readFileSync(file)), bytes: fs.statSync(file).size });
const rate = (numerator, denominator, denominatorUnit) => ({ numerator, denominator, value: denominator ? numerator / denominator : null, denominator_unit: denominatorUnit });
function requireValue(condition, message) { if (!condition) throw new Error(message); }
function jsonLines(file) {
  return fs.readFileSync(file, 'utf8').split(/\r?\n/).flatMap((raw, index) => raw.trim() ? [{ row: JSON.parse(raw), line: index + 1 }] : []);
}
function sameIds(actual, expected) { return isDeepStrictEqual([...actual].sort(), [...expected].sort()); }

function readLabelBasis(file = path.join(__dirname, 'codex-e2e-3-label-basis.json')) {
  const basis = readJson(file);
  requireValue(basis.oracle_sha256 === ORACLE_SHA256, 'Label basis oracle SHA256 differs from the approved pin');
  requireValue(sha256(fs.readFileSync(basis.oracle_file)) === ORACLE_SHA256, 'Cumulative oracle SHA256 mismatch; no fallback is permitted');
  const rows = new Map();
  for (const entry of jsonLines(basis.oracle_file)) {
    const row = entry.row;
    requireValue(typeof row.id === 'string' && !rows.has(row.id) && Array.isArray(row.pool), 'Invalid or duplicate oracle task');
    requireValue(row.pool.every(p => typeof p.skill === 'string') && new Set(row.pool.map(p => p.skill)).size === row.pool.length, `Duplicate or malformed oracle skill: ${row.id}`);
    rows.set(row.id, entry);
  }
  const related = [...rows.values()].filter(e => e.row.pool.some(p => typeof p.grade === 'number' && p.grade >= 2)).map(e => e.row.id);
  const none = [...rows.keys()].filter(id => !related.includes(id));
  requireValue(rows.size === 19 && related.length === 17 && none.length === 2, 'Pinned oracle does not have the approved 19/17/2 split');
  requireValue(sameIds(related, basis.related_task_ids) && sameIds(none, basis.no_related_task_ids), 'Label basis task classifications disagree with cumulative pool grades');
  return { rows, provenance: { basis: info(file), oracle: info(basis.oracle_file), task_count: rows.size, related_task_count: related.length, no_related_task_count: none.length, related_task_ids: related, no_related_task_ids: none } };
}

function joinLabels(taskId, ids, labels) {
  const entry = labels.get(taskId);
  requireValue(entry, `Task is absent from pinned labels: ${taskId}`);
  requireValue(ids === null || Array.isArray(ids) && ids.every(id => typeof id === 'string'), `Malformed returned IDs: ${taskId}`);
  const relatedIds = entry.row.pool.filter(p => typeof p.grade === 'number' && p.grade >= 2).map(p => p.skill);
  const loadedIds = ids === null ? null : unique(ids);
  const matches = loadedIds?.map(id => {
    const index = entry.row.pool.findIndex(p => p.skill === id);
    const candidate = index < 0 ? null : entry.row.pool[index];
    const graded = candidate && typeof candidate.grade === 'number' && Number.isFinite(candidate.grade);
    return { skill_id: id, grade: graded ? candidate.grade : null, grade_status: index < 0 ? 'NOT_IN_POOL' : graded ? 'GRADED' : 'MISSING_GRADE',
      oracle_line: entry.line, oracle_json_pointer: index < 0 ? null : `/pool/${index}`, added_in: candidate?.added_in ?? null };
  }) ?? null;
  const R = (matches || []).filter(m => m.grade !== null && m.grade >= 2).length;
  const N = (matches || []).filter(m => m.grade !== null && m.grade < 2).length;
  const U = (matches || []).filter(m => m.grade === null).length;
  const loaded = loadedIds === null ? null : loadedIds.length > 0;
  return { oracle_related: relatedIds.length > 0, oracle_relevant_skill_ids: relatedIds, loaded_skill_ids: loadedIds, loaded, oracle_matches: matches,
    relevance_counts: { relevant: R, graded_below_2: N, ungraded: U },
    observed_hit: loaded === null ? null : R > 0,
    hit_status: loaded === null ? 'UNRESOLVED_RETURN_EVIDENCE' : !loaded ? 'NOT_LOADED' : R > 0 ? 'CONFIRMED_RELEVANT_RETURN' : U > 0 ? 'UNRESOLVED_UNGRADED' : 'NO_RELEVANT_RETURN_OBSERVED',
    precision_graded: rate(R, R + N, 'graded unique returned skill IDs in this session'),
    confirmed_relevant_fraction: rate(R, R + N + U, 'all unique returned skill IDs in this session; lower bound when ungraded IDs exist') };
}

function aggregateMetrics(sessions) {
  const loaded = sessions.filter(s => s.loaded === true);
  const relatedLoaded = loaded.filter(s => s.oracle_related);
  const none = sessions.filter(s => !s.oracle_related);
  const gradedSessions = loaded.filter(s => s.precision_graded.denominator > 0);
  const sum = key => sessions.reduce((n, s) => n + s.relevance_counts[key], 0);
  const R = sum('relevant'), N = sum('graded_below_2'), U = sum('ungraded');
  const searches = sessions.flatMap(s => s.search_calls || []);
  const calls = sessions.flatMap(s => s.call_summaries || []);
  const cycleSessions = sessions.filter(s => s.cohort === 'codex' && s.skillfetch_called);
  return { selected_sessions: sessions.length, execution_started_sessions: sessions.filter(s => s.execution_started === true).length,
    related_task_sessions: sessions.filter(s => s.oracle_related).length, no_related_task_sessions: none.length,
    skillfetch_called_sessions: sessions.filter(s => s.skillfetch_called).length, searched_sessions: sessions.filter(s => s.searched).length,
    loaded_sessions: loaded.length, not_loaded_sessions: sessions.filter(s => s.loaded === false).length, ambiguous_return_sessions: sessions.filter(s => s.loaded === null).length,
    returned_ids: { relevant: R, graded_below_2: N, ungraded: U, total: R + N + U, path_ids: loaded.reduce((n, s) => n + s.loaded_skill_ids.filter(id => id.startsWith('path:')).length, 0) },
    hit_loaded_related: rate(relatedLoaded.filter(s => s.observed_hit).length, relatedLoaded.length, 'loaded sessions on tasks with at least one cumulative-oracle grade >= 2'),
    unresolved_loaded_related_sessions: relatedLoaded.filter(s => s.hit_status === 'UNRESOLVED_UNGRADED').length,
    hit_all_loaded_observed: rate(loaded.filter(s => s.observed_hit).length, loaded.length, 'all loaded sessions, including no-related-task sessions'),
    unresolved_all_loaded_sessions: loaded.filter(s => s.hit_status === 'UNRESOLVED_UNGRADED').length,
    precision_graded_micro: rate(R, R + N, 'graded unique full skill IDs per session, pooled across sessions'),
    precision_graded_macro: { value: gradedSessions.length ? gradedSessions.reduce((n, s) => n + s.precision_graded.value, 0) / gradedSessions.length : null,
      session_denominator: gradedSessions.length, excluded_loaded_sessions_without_grades: loaded.length - gradedSessions.length,
      definition: 'Unweighted mean of each loaded session R/(R+N), including only sessions with at least one graded returned ID.' },
    confirmed_relevant_fraction_all_returned: rate(R, R + N + U, 'all unique returned IDs per session; lower bound when ungraded IDs exist'),
    graded_coverage: rate(R + N, R + N + U, 'all unique returned IDs per session'), unknown_coverage: rate(U, R + N + U, 'all unique returned IDs per session'),
    sessions_with_ungraded_returns: loaded.filter(s => s.relevance_counts.ungraded > 0).length,
    none_task_loading: { selected_sessions: none.length, searched_sessions: none.filter(s => s.searched).length, loaded_sessions: none.filter(s => s.loaded === true).length,
      ambiguous_return_sessions: none.filter(s => s.loaded === null).length,
      loaded_among_all: rate(none.filter(s => s.loaded === true).length, none.length, 'all selected sessions on tasks with zero cumulative-oracle grade >= 2'),
      loaded_among_searched: rate(none.filter(s => s.searched && s.loaded === true).length, none.filter(s => s.searched).length, 'searched sessions on no-related tasks'),
      graded_below_2_ids: none.reduce((n, s) => n + s.relevance_counts.graded_below_2, 0), ungraded_ids: none.reduce((n, s) => n + s.relevance_counts.ungraded, 0) },
    result_status_counts: counts(sessions.map(s => s.result_status ?? 'UNOBSERVED')), model_session_counts: counts(sessions.map(s => s.model ?? 'UNOBSERVED')),
    skillfetch_tool_call_counts: counts(calls.map(c => c.tool)), protocol_status_counts: counts(calls.map(c => c.protocol_status ?? 'UNOBSERVED')),
    server_call_observations: { total_calls: calls.length, calls_with_result_presence_evidence: calls.filter(c => typeof c.server_result_received === 'boolean').length,
      received_result: calls.filter(c => c.server_result_received === true).length, calls_with_protocol_outcome: calls.filter(c => typeof c.protocol_success === 'boolean').length,
      protocol_success: calls.filter(c => c.protocol_success === true).length, protocol_failure: calls.filter(c => c.protocol_success === false).length,
      approval_denied: calls.filter(c => c.approval_denied === true).length },
    load_call_count: sessions.reduce((n, s) => n + (s.load_calls?.length || 0), 0),
    load_protocol_status_counts: counts(sessions.flatMap(s => (s.load_calls || []).map(c => c.protocol_status ?? 'UNOBSERVED'))),
    load_semantic_status_counts: counts(sessions.flatMap(s => (s.load_calls || []).map(c => c.semantic_status ?? c.return_status ?? 'UNOBSERVED'))),
    load_return_conflicts: sessions.reduce((n, s) => n + (s.load_calls || []).filter(c => c.return_conflict || c.conflict).length, 0),
    prompt_submission_checks: { applicable_codex_sessions: sessions.filter(s => s.cohort === 'codex').length,
      observed_turn_start_count: sessions.reduce((n, s) => n + (s.prompt_submission?.count || 0), 0),
      exact_matches: sessions.filter(s => s.prompt_submission?.exact_frozen_prompt_match === true).length,
      mismatches: sessions.filter(s => s.prompt_submission?.exact_frozen_prompt_match === false).length },
    query_check_status_counts: counts(searches.map(c => c.query_check_status)), query_checks_observed: searches.length,
    first_call_model_response_cycle: { applicable_codex_called_sessions: cycleSessions.length, mapped_sessions: cycleSessions.filter(s => s.first_call?.model_response_cycle != null).length,
      unknown_sessions: cycleSessions.filter(s => s.first_call?.model_response_cycle == null).length,
      cycle_counts: counts(cycleSessions.filter(s => s.first_call?.model_response_cycle != null).map(s => s.first_call.model_response_cycle)), mapping_counts: counts(cycleSessions.map(s => s.first_call?.model_response_cycle_mapping ?? 'UNOBSERVED')) } };
}
function cohortMetrics(sessions) {
  return { per_replicate: Object.fromEntries(REPLICATES.map(r => [r, aggregateMetrics(sessions.filter(s => s.replicate === r))])), pooled: aggregateMetrics(sessions) };
}
function inRoot(root, target) {
  const relative = path.relative(root, target);
  return relative !== '' && relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}
function outputPath(root, file) {
  const resolved = path.join(fs.realpathSync(path.dirname(file)), path.basename(file));
  requireValue(inRoot(root, resolved), `Output must be inside the new run root: ${file}`);
  return resolved;
}
function submissionEvidence(task, prompt) {
  if (!task.evidence.transcript_present) return { count: 0, exact_frozen_prompt_match: null, events: [] };
  const entries = jsonLines(task.evidence.transcript).filter(e => e.row.direction === 'send' && e.row.message?.method === 'turn/start');
  const events = entries.map(e => {
    const input = e.row.message.params?.input;
    const text = Array.isArray(input) && input.length === 1 && input[0].type === 'text' ? input[0].text : null;
    return { event_sequence: e.row.sequence, transcript_line: e.line, exact_prompt_match: typeof text === 'string' ? text === prompt : null, submitted_prompt_sha256: typeof text === 'string' ? sha256(text) : null };
  });
  requireValue(entries.length <= 1, `Duplicate task submission: ${task.id}`);
  requireValue(task.manifest.execution_started !== true || entries.length === 1, `Missing turn/start for started task: ${task.id}`);
  return { count: entries.length, exact_frozen_prompt_match: entries.length === 1 ? events[0].exact_prompt_match : null, events };
}

function extractExperiment(options) {
  const root = fs.realpathSync(options.runRoot);
  const label = readLabelBasis(options.labelBasis);
  const paths = REPLICATES.map(r => fs.realpathSync(options.runDirs?.[r] || path.join(root, r)));
  requireValue(new Set(paths).size === 3 && paths.every(p => inRoot(root, p)), 'Three distinct replicate directories must be inside the new run root');
  const perRuns = REPLICATES.map((replicate, index) => {
    const directory = paths[index], manifest = readJson(path.join(directory, 'manifest.json'));
    requireValue(['COMPLETED', 'COMPLETED_WITH_FAILURES'].includes(manifest.status) && typeof manifest.finished_at === 'string', `Run is not terminal/finished: ${replicate}`);
    const observed = extractRun(directory);
    requireValue(observed.frozen_tasks.status === 'VERIFIED', `Unverified frozen task file: ${replicate}`);
    requireValue(sameIds(observed.tasks.map(t => t.id), label.rows.keys()), `Replicate task IDs differ from label basis: ${replicate}`);
    const file = outputPath(root, path.join(directory, 'observations-e2e3.json'));
    const value = { ...observed, experiment_replicate: replicate };
    const bytes = `${JSON.stringify(value, null, 2)}\n`;
    return { replicate, directory, file, bytes, observed, manifest_source: info(path.join(directory, 'manifest.json')), observations_sha256: sha256(bytes) };
  });
  for (const run of perRuns.slice(1)) for (const key of ['source_commit', 'codex_version', 'tasks_sha256', 'config_sha256', 'agents_sha256', 'cloud_skills_sha256', 'repository_refs', 'requested_model', 'assistant_round_cap']) {
    requireValue(isDeepStrictEqual(perRuns[0].observed.manifest[key], run.observed.manifest[key]), `Replicate configuration differs: ${key}`);
  }
  for (const key of ['source_commit', 'codex_version', 'tasks_sha256', 'config_sha256', 'agents_sha256', 'cloud_skills_sha256', 'repository_refs']) {
    requireValue(perRuns[0].observed.manifest[key] !== undefined, `Missing frozen replicate configuration: ${key}`);
  }
  const frozen = jsonLines(path.join(paths[0], 'tasks.jsonl'));
  const prompts = new Map(frozen.map(e => [e.row.id, e.row.prompt]));
  const lengths = frozen.map(e => ({ task_id: e.row.id, characters: [...e.row.prompt].length, utf16_code_units: e.row.prompt.length,
    utf8_bytes: Buffer.byteLength(e.row.prompt, 'utf8'), at_least_800: [...e.row.prompt].length >= 800, prompt_sha256: sha256(e.row.prompt), frozen_task_line: e.line }));
  const codex = perRuns.flatMap(run => run.observed.tasks.map((task, index) => {
    requireValue(task.frozen_prompt.status === 'VERIFIED', `Unverified task prompt: ${run.replicate}/${task.id}`);
    const submission = submissionEvidence(task, prompts.get(task.id));
    const ids = task.evidence.transcript_present ? task.returned_skill_ids : null;
    return { cohort: 'codex', task_id: task.id, replicate: run.replicate, session_key: `${run.replicate}/${task.id}`,
      observation_file: run.file, observation_json_pointer: `/tasks/${index}`, evidence: task.evidence,
      execution_started: task.manifest.execution_started === true, result_status: task.status, model: task.manifest.model ?? null,
      manifest: task.manifest, prompt_submission: submission, skillfetch_called: task.skillfetch_called, searched: task.search_calls.length > 0,
      outer_user_turn_index: task.outer_user_turn_index, first_call: task.first_call, skillfetch_call_count: task.skillfetch_call_count,
      skillfetch_call_attempt_count: task.skillfetch_call_attempt_count, approval_denied_call_count: task.approval_denied_call_count,
      server_result_count: task.server_result_count, successful_server_call_count: task.successful_server_call_count,
      call_summaries: task.calls.map(c => ({ id: c.id, tool: c.tool, event_sequence: c.event_sequence, status: c.status, protocol_status: c.protocol_status,
        protocol_success: c.protocol_success, server_result_received: c.server_result_received, server_success_observed: c.server_success_observed,
        approval_denied: c.approval_denied, error: c.error })),
      search_calls: task.search_calls,
      load_calls: task.load_calls.map(c => ({ id: c.id, event_sequence: c.event_sequence, status: c.status, protocol_status: c.protocol_status, semantic_status: c.semantic_status,
        return_conflict: c.return_conflict, returned_skill_ids: c.returned_skill_ids, payload_errors: c.payload_errors })),
      raw_load_return_occurrences: task.load_calls.flatMap(c => c.returned_skill_ids || []), confirmed_returned_skill_ids: task.confirmed_returned_skill_ids,
      turn_end_events: task.turn_end_events, process_exit_events: task.process_exit_events, warnings: task.warnings,
      ...joinLabels(task.id, ids, label.rows) };
  }));
  const threadIds = codex.filter(s => s.execution_started && typeof s.manifest.thread_id === 'string').map(s => s.manifest.thread_id);
  requireValue(unique(threadIds).length === threadIds.length, 'Thread ID reused across replicate/task sessions');
  const claudeFile = options.claudeFile || path.join(__dirname, 'codex-e2e-2-oracle-v2.json');
  const claudeSource = readJson(claudeFile);
  requireValue(claudeSource.provenance?.tasks?.sha256 === perRuns[0].observed.frozen_tasks.actual_sha256, 'Claude V2 task-source SHA256 differs from frozen Codex tasks');
  requireValue(Array.isArray(claudeSource.sessions) && claudeSource.sessions.length === 57, 'Claude V2 source must contain exactly 57 sessions');
  const claude = claudeSource.sessions.map((session, index) => {
    requireValue(REPLICATES.includes(session.tag) && prompts.has(session.task_id), 'Unknown Claude task or replicate');
    requireValue(session.prompt_matches === true && session.task_prompt_sha256 === sha256(prompts.get(session.task_id)), `Claude prompt mismatch: ${session.task_id}/${session.tag}`);
    return { cohort: 'claude_v2', task_id: session.task_id, replicate: session.tag, session_key: `${session.tag}/${session.task_id}`,
      observation_file: claudeFile, observation_json_pointer: `/sessions/${index}`, log_file: session.log_file, log_sha256: session.log_sha256 ?? null,
      meta_file: session.meta_file, meta_sha256: session.meta_sha256 ?? null, execution_started: session.init_count === 1,
      result_status: session.result_status, model: session.init_evidence?.[0]?.model ?? null, prompt_matches: session.prompt_matches,
      skillfetch_called: session.skillfetch_tool_calls?.length > 0, searched: session.skillfetch_tool_calls?.some(c => c.name === 'mcp__skillfetch__search_skills') ?? false,
      call_summaries: (session.skillfetch_tool_calls || []).map(c => ({ id: c.tool_use_id, tool: c.name.replace(/^mcp__skillfetch__/, ''), transcript_line: c.line })),
      load_calls: session.load_calls, raw_load_return_occurrences: session.loaded_skill_occurrences ?? null,
      warnings: session.warnings || [], ...joinLabels(session.task_id, session.loaded_skill_ids, label.rows) };
  });
  for (const sessions of [codex, claude]) {
    requireValue(new Set(sessions.map(s => s.session_key)).size === 57, 'Duplicate or missing task/replicate session');
    for (const replicate of REPLICATES) requireValue(sameIds(sessions.filter(s => s.replicate === replicate).map(s => s.task_id), prompts.keys()), `Incomplete ${replicate} task matrix`);
  }
  const cell = session => ({ session_key: session.session_key, loaded_skill_ids: session.loaded_skill_ids, raw_load_return_occurrences: session.raw_load_return_occurrences,
    relevance_counts: session.relevance_counts, oracle_matches: session.oracle_matches, hit_status: session.hit_status, result_status: session.result_status });
  const taskSets = lengths.map(length => ({ ...length, oracle_related: label.rows.get(length.task_id).row.pool.some(p => typeof p.grade === 'number' && p.grade >= 2),
    codex: Object.fromEntries(REPLICATES.map(r => [r, cell(codex.find(s => s.task_id === length.task_id && s.replicate === r))])),
    claude_v2: Object.fromEntries(REPLICATES.map(r => [r, cell(claude.find(s => s.task_id === length.task_id && s.replicate === r))])) }));
  const combined = { schema_version: 3, generated_at: new Date().toISOString(), analysis_type: 'OFFLINE_EXISTING_RECORDINGS', run_root: root,
    source_evidence_kinds: perRuns.map(r => ({ replicate: r.replicate, kind: r.observed.source_evidence_kind })),
    sources: { extractor: info(__filename), reused_extractor: info(path.join(__dirname, 'codex-e2e-2-extract.cjs')), claude_v2: info(claudeFile),
      runs: perRuns.map(r => ({ replicate: r.replicate, run_directory: r.directory, manifest: r.manifest_source, observations_file: r.file, observations_sha256: r.observations_sha256, frozen_tasks: r.observed.frozen_tasks })) },
    label_basis: label.provenance,
    units: { ...perRuns[0].observed.units, request_characters: 'Unicode code points in the original frozen prompt, without trimming or normalization; threshold >= 800.',
      metrics_returned_ids: 'Unique exact full returned skill IDs within a task/replicate session. The same ID counts separately across sessions; raw per-load occurrences are also preserved.',
      claude_labels: 'Only loaded_skill_ids from the prior Claude V2 extraction are reused. Its prior oracle grades are ignored and every ID is rejoined to the pinned cumulative oracle.',
      observed_hits: 'R > 0. Sessions with R=0 and U>0 remain unresolved and are listed separately; the observed numerator over all eligible loaded sessions is a lower bound.',
      unknowns: 'Missing task-specific full-ID grades remain null; path IDs are never normalized or assigned grades.',
      precision_macro: 'Mean of per-session graded-only precision among loaded sessions with at least one graded returned ID; denominator explicitly excludes sessions with no graded returned IDs.' },
    limitations: [...perRuns[0].observed.limitations, 'No task-result or code-quality grades are assigned.', 'The Claude comparison reuses previously extracted load returns and revalidates prompt hashes; its logs are referenced rather than reexecuted.', 'Ambiguous return sets remain null and are excluded from ID precision and loaded-session denominators, with counts shown separately.'],
    request_lengths: lengths, long_request_task_ids: lengths.filter(l => l.at_least_800).map(l => l.task_id),
    metrics: { codex: cohortMetrics(codex), claude_v2: cohortMetrics(claude) }, sessions: { codex, claude_v2: claude }, task_sets: taskSets,
    warnings: [...codex, ...claude].flatMap(s => s.warnings.map(warning => ({ cohort: s.cohort, session_key: s.session_key, warning }))) };
  return { combined, perRuns };
}

function writeExperiment(extracted, options) {
  const root = fs.realpathSync(options.runRoot);
  const out = outputPath(root, options.out || path.join(root, 'observations-e2e3.json'));
  const files = [...extracted.perRuns.map(r => ({ file: outputPath(root, r.file), bytes: r.bytes })), { file: out, bytes: `${JSON.stringify(extracted.combined, null, 2)}\n` }];
  requireValue(new Set(files.map(f => f.file)).size === files.length, 'Output paths must be distinct');
  for (const file of files) requireValue(!fs.existsSync(file.file), `Output exists; refusing to overwrite evidence: ${file.file}`);
  for (const file of files) fs.writeFileSync(file.file, file.bytes, { flag: 'wx', mode: 0o600 });
  return files.map(f => ({ file: f.file, sha256: sha256(f.bytes) }));
}
function parseArgs(argv) {
  if (argv.length === 1 && ['-h', '--help'].includes(argv[0])) return { help: true };
  const args = {};
  for (let i = 0; i < argv.length; i += 2) {
    requireValue(['--run-root', '--r1-dir', '--r2-dir', '--r3-dir', '--out'].includes(argv[i]) && !args[argv[i]] && argv[i + 1] && !argv[i + 1].startsWith('--'), `Invalid argument: ${argv[i]}`);
    args[argv[i]] = path.resolve(argv[i + 1]);
  }
  requireValue(args['--run-root'], HELP.trim());
  return { runRoot: args['--run-root'], runDirs: Object.fromEntries(REPLICATES.map(r => [r, args[`--${r}-dir`] || path.join(args['--run-root'], r)])), out: args['--out'] || path.join(args['--run-root'], 'observations-e2e3.json') };
}
module.exports = { joinLabels, aggregateMetrics, readLabelBasis, extractExperiment, writeExperiment, parseArgs };
if (require.main === module) {
  try { const options = parseArgs(process.argv.slice(2)); if (options.help) process.stdout.write(HELP); else process.stdout.write(`${JSON.stringify(writeExperiment(extractExperiment(options), options), null, 2)}\n`); }
  catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
}
