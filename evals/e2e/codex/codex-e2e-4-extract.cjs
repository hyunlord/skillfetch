#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { isDeepStrictEqual } = require('node:util');
const { extractRun } = require('./codex-e2e-2-extract.cjs');
const { readLabelBasis, joinLabels, aggregateMetrics: aggregateV3, writeExperiment } = require('./codex-e2e-3-extract.cjs');
const REPLICATES = ['r1', 'r2', 'r3'];
const BASELINE_FILE = path.join(__dirname, 'codex-e2e-3-runs/20261024-full-router-14d2020/observations-e2e3.json');
const BASELINE_SHA256 = '850b13fe8a45b261fad56d8192db2f9603a3e716b2a78fd68083e3f3a0e927fa';
const FIXED_KEYS = ['source_commit', 'codex_version', 'tasks_sha256', 'config_sha256', 'cloud_skills_sha256', 'repository_refs', 'requested_model', 'assistant_round_cap', 'timeout_seconds'];
const ACTION_TYPES = new Set(['commandExecution', 'fileChange', 'mcpToolCall', 'dynamicToolCall', 'collabAgentToolCall', 'webSearch', 'imageView', 'sleep', 'imageGeneration']);
const HELP = 'Usage: node codex-e2e-4-extract.cjs --run-root DIR [--r1-dir DIR --r2-dir DIR --r3-dir DIR] [--out FILE]\nOffline extraction only; requires three finished runs. Defaults: DIR/r1,r2,r3 and DIR/observations-e2e4.json.\n';
const unique = xs => [...new Set(xs)];
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const present = x => x === undefined ? null : x;
const sha256 = x => crypto.createHash('sha256').update(x).digest('hex');
const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const info = file => ({ file, sha256: sha256(fs.readFileSync(file)), bytes: fs.statSync(file).size });
const counts = xs => xs.reduce((out, x) => { out[String(x)] = (out[String(x)] || 0) + 1; return out; }, {});
const rate = (numerator, denominator, unit) => ({ numerator, denominator, value: denominator ? numerator / denominator : null, denominator_unit: unit });
function ensure(condition, message) { if (!condition) throw new Error(message); }
function sameIds(a, b) { return isDeepStrictEqual([...a].sort(), [...b].sort()); }
function jsonLines(file) { return fs.readFileSync(file, 'utf8').split(/\r?\n/).flatMap((line, i) => line.trim() ? [{ ...JSON.parse(line), line_number: i + 1 }] : []); }
function inside(root, file) { const r = path.relative(root, file); return r !== '' && r !== '..' && !r.startsWith(`..${path.sep}`) && !path.isAbsolute(r); }

// V2 response-cycle readers, copied unchanged so a child-first event cannot determine the primary first-call cycle.
function responseCycles(events, warnings) {
  const scopes = new Map();
  const functions = [];
  const methods = new Set();
  for (const event of events) {
    if (event.direction !== 'receive' || !object(event.message)) continue;
    const { method, params } = event.message;
    if (typeof method !== 'string' || !/raw.*response|response.*raw/i.test(method)) continue;
    methods.add(method);
    const normalized = method.toLowerCase();
    if (!['rawresponse/completed', 'rawresponseitem/completed'].includes(normalized)) {
      warnings.push(`Unsupported raw-event method ${method}; its undocumented payload is not interpreted.`); continue;
    }
    if (!object(params) || typeof params.threadId !== 'string' || typeof params.turnId !== 'string') {
      warnings.push(`Raw event ${event.sequence} has no threadId/turnId scope.`); continue;
    }
    const key = JSON.stringify([params.threadId, params.turnId]);
    if (!scopes.has(key)) scopes.set(key, { responses: new Map(), pending: [] });
    const scope = scopes.get(key);
    if (normalized === 'rawresponseitem/completed') {
      const item = params.item;
      if (object(item) && ['function_call', 'custom_tool_call'].includes(item.type) && typeof item.call_id === 'string') {
        const call = { call_id: item.call_id, name: present(item.name), type: item.type, thread_id: params.threadId, turn_id: params.turnId,
          input: present(item.input), output_event_sequence: null, output_terminal: null,
          event_sequence: event.sequence, model_response_cycle: null, response_id: null, boundary_event_sequence: null };
        functions.push(call); scope.pending.push(call);
      } else if (object(item) && ['function_call_output', 'custom_tool_call_output'].includes(item.type)) {
        for (const call of functions.filter(call => call.call_id === item.call_id && call.thread_id === params.threadId && call.turn_id === params.turnId && call.output_event_sequence === null)) {
          const output = typeof item.output === 'string' ? item.output : item.output?.[0]?.text;
          call.output_event_sequence = event.sequence;
          call.output_terminal = call.name !== 'exec' || typeof output === 'string' && /^Script (?:completed|failed)(?:\r?\n|$)/.test(output);
        }
      }
    } else if (typeof params.responseId !== 'string' || !params.responseId) {
      warnings.push(`Raw completion ${event.sequence} has no usable responseId.`);
    } else if (!scope.responses.has(params.responseId)) {
      scope.responses.set(params.responseId, scope.responses.size + 1);
      for (const call of scope.pending) Object.assign(call, { model_response_cycle: scope.responses.size, response_id: params.responseId, boundary_event_sequence: event.sequence });
      scope.pending = [];
    }
  }
  return { functions, methods: [...methods], completed_response_count: [...scopes.values()].reduce((total, scope) => total + scope.responses.size, 0) };
}

function firstCall(call, raw, warnings) {
  if (!call) return null;
  const scoped = raw.functions.filter(item => item.thread_id === call.thread_id && item.turn_id === call.turn_id);
  let matches = scoped.filter(item => item.call_id === call.id);
  let method = 'direct_call_id';
  if (!matches.length && call.started && call.completed) {
    const overlapping = scoped.filter(item => item.event_sequence < Math.max(...call.event_sequences) &&
      (item.output_event_sequence === null || !item.output_terminal || item.output_event_sequence > call.event_sequence));
    const candidate = overlapping[0];
    if (overlapping.length === 1 && candidate.type === 'custom_tool_call' && candidate.name === 'exec' && candidate.output_terminal &&
      candidate.event_sequence < call.event_sequence && candidate.output_event_sequence > Math.max(...call.event_sequences) &&
      typeof candidate.input === 'string' && candidate.input.includes(`tools.mcp__skillfetch__${call.tool}(`)) {
      matches = [candidate]; method = 'unique_closed_code_exec_interval';
    }
  }
  const identities = unique(matches.map(item => JSON.stringify([item.model_response_cycle, item.response_id, item.name])));
  const mapped = matches.length > 0 && identities.length === 1 && matches[0].model_response_cycle !== null && warnings.length === 0;
  return { id: call.id, tool: call.tool, event_sequence: call.event_sequence, transcript_line: call.transcript_line,
    action_ordinal: call.action_ordinal, item_ordinal: call.item_ordinal, at: call.at,
    model_response_cycle: mapped ? matches[0].model_response_cycle : null,
    model_response_cycle_mapping: mapped ? method : null,
    model_response_cycle_explanation: mapped ? (method === 'direct_call_id' ? 'Exact raw call_id equals MCP item.id in the same thread/turn; cycle is the ordinal of its following unique responseId completion.' :
      'Derived from the sole closed exec interval enclosing both MCP lifecycle events in the same thread/turn, with matching literal tool-call syntax and no overlapping or previously yielded call; parentage is inferred, not an explicit parent ID.') :
      (warnings.length ? 'Incomplete, unsupported, or inconsistent transcript evidence prevents a reliable raw response-cycle assignment.' : matches.length === 0 ? 'No raw function/custom-tool call with this MCP item ID and thread/turn was observed; event/action ordinals are separate units.' : 'Raw call mapping is ambiguous or its model response has no observed completion boundary.'),
    raw_call_matches: matches };
}

function noLoadEvidence(task, events, calls, searches, loads, ids, primaryId) {
  const successfulEmpty = loads.filter(c => c.protocol_success === true && c.semantic_status === 'SUCCESS' && !c.return_conflict && Array.isArray(c.returned_skill_ids) && c.returned_skill_ids.length === 0);
  const failureCalls = calls.filter(c => c.protocol_success === false || c.error != null).map(c => ({ id: c.id, tool: c.tool, event_sequence: c.event_sequence, transcript_line: c.transcript_line, protocol_status: c.protocol_status, error: c.error }));
  const semanticErrors = loads.filter(c => ['ERROR', 'MALFORMED', 'MIXED'].includes(c.semantic_status)).map(c => ({ id: c.id, event_sequence: c.event_sequence, semantic_status: c.semantic_status, payload_errors: c.payload_errors }));
  const firstSearch = searches.length ? Math.min(...searches.map(c => c.event_sequence)) : null;
  const scoped = events.filter(e => e.direction === 'receive' && e.message?.params?.threadId === primaryId);
  const codeWork = scoped.filter(e => ['item/started', 'item/completed'].includes(e.message?.method) && ['commandExecution', 'fileChange'].includes(e.message.params?.item?.type) && (firstSearch === null || e.sequence > firstSearch));
  const firstCode = codeWork.length ? Math.min(...codeWork.map(e => e.sequence)) : null;
  const messages = scoped.filter(e => e.message?.method === 'item/completed' && e.message.params?.item?.type === 'agentMessage' && typeof e.message.params.item.text === 'string' && (firstSearch === null || e.sequence > firstSearch));
  const excerpts = messages.slice(0, 12).map(e => ({ event_sequence: e.sequence, transcript_line: e.line_number, item_id: e.message.params.item.id ?? null,
    phase: e.message.params.item.phase ?? null, text: e.message.params.item.text.slice(0, 1600), text_truncated: e.message.params.item.text.length > 1600,
    full_text_sha256: sha256(e.message.params.item.text), after_search: firstSearch !== null, before_first_code_work: firstCode === null || e.sequence < firstCode }));
  const emptyArguments = calls.filter(c => c.tool === 'resolve_set').flatMap(c => c.argument_observations.flatMap(o => {
    let args = o.arguments; if (typeof args === 'string') { try { args = JSON.parse(args); } catch { return []; } }
    return object(args) && Array.isArray(args.auto_ids) && args.auto_ids.length === 0 && (args.pinned_ids === undefined || Array.isArray(args.pinned_ids) && args.pinned_ids.length === 0)
      ? [{ id: c.id, event_sequence: o.event_sequence, arguments: args }] : [];
  }));
  let status = 'NO_LOAD_CALL';
  if (ids === null) status = 'UNRESOLVED_RETURN_EVIDENCE';
  else if (ids.length) status = 'RETURNED_SKILLS';
  else if (loads.some(c => c.protocol_success === false)) status = 'LOAD_PROTOCOL_FAILURE';
  else if (semanticErrors.length) status = 'LOAD_SEMANTIC_ERROR';
  else if (loads.length && successfulEmpty.length === loads.length) status = 'EMPTY_SUCCESSFUL_LOAD';
  else if (loads.length) status = 'LOAD_RESULT_UNRESOLVED';
  return { status, load_call_count: loads.length, successful_empty_loads: successfulEmpty.map(c => ({ id: c.id, event_sequence: c.event_sequence, semantic_status: c.semantic_status })),
    tool_failures: failureCalls, semantic_errors: semanticErrors, empty_resolve_selection_arguments: emptyArguments,
    explicit_none_confirmed: null, explicit_none_review_status: ids?.length ? 'NOT_APPLICABLE_RETURNED_SKILLS' : 'UNREVIEWED',
    decision_excerpts: excerpts, excerpt_counts: { available: messages.length, retained: excerpts.length, omitted: messages.length - excerpts.length },
    first_search_event_sequence: firstSearch, first_code_work_event_sequence: firstCode,
    interpretation: 'No-load is an observed outcome, not an inferred deliberate none selection. Excerpts and empty arguments require human review; no keyword-based intent classification is applied.' };
}

function primaryThreadTask(task, events) {
  const primaryId = typeof task.manifest.thread_id === 'string' ? task.manifest.thread_id : null;
  ensure(!task.warnings.some(w => /MCP item ID .* conflicting identity fields/.test(w)), `Cannot partition conflicting MCP identity: ${task.id}`);
  const warnings = [...task.warnings];
  const scoped = task.calls.filter(c => primaryId !== null && c.thread_id === primaryId);
  const nonprimary = task.calls.filter(c => typeof c.thread_id === 'string' && c.thread_id !== primaryId);
  const unscoped = task.calls.filter(c => typeof c.thread_id !== 'string');
  const actions = new Set(), items = new Set(), ordinals = new Map();
  for (const e of events) {
    if (e.direction !== 'receive' || e.message?.params?.threadId !== primaryId || !['item/started', 'item/completed'].includes(e.message?.method)) continue;
    const item = e.message.params.item; if (!object(item) || typeof item.id !== 'string') continue;
    items.add(item.id); if (ACTION_TYPES.has(item.type)) actions.add(item.id);
    if (!ordinals.has(item.id)) ordinals.set(item.id, { item_ordinal: items.size, action_ordinal: actions.size });
  }
  const calls = scoped.map(c => ({ ...c, all_thread_item_ordinal: c.item_ordinal, all_thread_action_ordinal: c.action_ordinal,
    item_ordinal: ordinals.get(c.id)?.item_ordinal ?? null, action_ordinal: ordinals.get(c.id)?.action_ordinal ?? null }));
  const subset = selected => {
    const ids = new Set(selected.map(c => c.id));
    const loads = task.load_calls.filter(c => ids.has(c.id));
    return { calls: selected, search_calls: task.search_calls.filter(c => ids.has(c.id)), load_calls: loads,
      returned_skill_ids: loads.some(c => c.return_conflict) ? null : unique(loads.flatMap(c => c.returned_skill_ids || [])) };
  };
  const main = subset(calls), other = subset(nonprimary), unknown = subset(unscoped);
  const primaryScopeCertain = primaryId !== null && unscoped.length === 0;
  const confirmedIds = unique(main.load_calls.flatMap(c => c.returned_skill_ids || []));
  const ids = !primaryScopeCertain || !task.evidence.transcript_present || main.load_calls.some(c => c.return_conflict) ? null : confirmedIds;
  const raw = responseCycles(events.filter(e => e.message?.params?.threadId === primaryId), warnings);
  if (!primaryScopeCertain) warnings.push('Primary MCP scope is uncertain: absent primary thread ID or unscoped MCP calls.');
  const first = firstCall(calls[0], raw, warnings);
  const primaryTurnEndSequences = new Set(events.filter(e => e.message?.method === 'turn/completed' && e.message.params?.threadId === primaryId).map(e => e.sequence));
  return { ...task, primary_thread_id: primaryId, primary_scope_certain: primaryScopeCertain, primary_action_ordinal_unit: 'Distinct actionable items in the primary thread only.',
    all_thread_first_call: task.first_call, all_thread_skillfetch_call_count: task.skillfetch_call_count,
    nonprimary_thread_observations: { ...other, thread_ids: unique(nonprimary.map(c => c.thread_id)), classification: 'Explicitly different thread IDs; kept separate from primary-thread metrics without assuming a parent-child relation.' },
    unscoped_thread_observations: unknown, calls, search_calls: main.search_calls, load_calls: main.load_calls,
    skillfetch_called: calls.length > 0, skillfetch_call_count: calls.length, skillfetch_call_attempt_count: calls.length,
    approval_denied_call_count: calls.filter(c => c.approval_denied).length, server_result_count: calls.filter(c => c.server_result_received).length,
    successful_server_call_count: calls.filter(c => c.server_success_observed).length,
    first_call: first, load_return_conflict: main.load_calls.some(c => c.return_conflict), confirmed_returned_skill_ids: confirmedIds, returned_skill_ids: ids,
    observed_completed_model_responses: raw.completed_response_count, raw_response_methods: raw.methods,
    turn_end_events: task.turn_end_events.filter(e => primaryTurnEndSequences.has(e.event_sequence)),
    no_load_evidence: noLoadEvidence(task, events, calls, main.search_calls, main.load_calls, ids, primaryId), warnings: unique(warnings) };
}

function aggregateMetrics(sessions) {
  const base = aggregateV3(sessions);
  const related = sessions.filter(s => s.oracle_related);
  const knownIds = sessions.reduce((n, s) => n + (Array.isArray(s.loaded_skill_ids) ? s.loaded_skill_ids.length : 0), 0);
  const ambiguous = sessions.filter(s => s.loaded_skill_ids === null).length;
  const mean = rate(knownIds, sessions.length, 'all selected sessions; known zero-load sessions contribute zero');
  return { ...base,
    hit_all_related: rate(related.filter(s => s.observed_hit === true).length, related.length, 'PRIMARY: all selected tasks with at least one cumulative-oracle grade >= 2, including zero-load and uncertain sessions'),
    hit_all_related_unresolved_sessions: related.filter(s => s.loaded === null || s.hit_status === 'UNRESOLVED_UNGRADED').length,
    hit_all_related_known_zero_load_sessions: related.filter(s => s.loaded === false).length,
    hit_loaded_related_is_secondary: true,
    mean_distinct_returned_ids_per_selected_session: { ...mean, value: ambiguous ? null : mean.value, observed_lower_bound_value: mean.value, ambiguous_session_count: ambiguous },
    no_load_evidence_status_counts: counts(sessions.map(s => s.no_load_evidence?.status ?? 'UNOBSERVED')),
    no_load_with_tool_failure_sessions: sessions.filter(s => s.loaded === false && (s.no_load_evidence?.tool_failures?.length || s.no_load_evidence?.semantic_errors?.length)).length,
    successful_empty_load_call_count: sessions.reduce((n, s) => n + (s.no_load_evidence?.successful_empty_loads?.length || 0), 0),
    explicit_none_review: { confirmed_session_count: null, reviewed_session_count: 0, unreviewed_no_load_sessions: sessions.filter(s => s.no_load_evidence?.explicit_none_review_status === 'UNREVIEWED').length, method: 'No automatic intent classification; root review of cited excerpts is required.' },
    nonprimary_thread_mcp_call_count: sessions.reduce((n, s) => n + (s.nonprimary_thread_observations?.calls.length || 0), 0),
    unscoped_mcp_call_count: sessions.reduce((n, s) => n + (s.unscoped_thread_observations?.calls.length || 0), 0) };
}
function cohortMetrics(sessions) { return { per_replicate: Object.fromEntries(REPLICATES.map(r => [r, aggregateMetrics(sessions.filter(s => s.replicate === r))])), pooled: aggregateMetrics(sessions) }; }
function rawTotals(tasks) {
  const searches = tasks.flatMap(t => t.search_calls), loads = tasks.flatMap(t => t.load_calls);
  return { task_count: tasks.length, execution_started_count: tasks.filter(t => t.manifest.execution_started === true).length, skillfetch_called_count: tasks.filter(t => t.skillfetch_called).length,
    skillfetch_call_count: tasks.reduce((n, t) => n + t.skillfetch_call_count, 0), server_result_count: tasks.reduce((n, t) => n + t.server_result_count, 0),
    successful_server_call_count: tasks.reduce((n, t) => n + t.successful_server_call_count, 0), approval_denied_call_count: tasks.reduce((n, t) => n + t.approval_denied_call_count, 0),
    search_call_count: searches.length, search_query_check_status_counts: counts(searches.map(c => c.query_check_status)),
    load_call_count: loads.length, load_return_conflict_count: loads.filter(c => c.return_conflict).length, task_status_counts: counts(tasks.map(t => t.status)),
    nonprimary_thread_call_count: tasks.reduce((n, t) => n + t.nonprimary_thread_observations.calls.length, 0), unscoped_call_count: tasks.reduce((n, t) => n + t.unscoped_thread_observations.calls.length, 0) };
}
function scopeRun(observed) {
  const tasks = observed.tasks.map(task => primaryThreadTask(task, task.evidence.transcript_present ? jsonLines(task.evidence.transcript) : []));
  return { ...observed, schema_version: 4, reused_parser_schema_version: observed.schema_version, all_thread_totals: observed.totals, totals: rawTotals(tasks), tasks,
    primary_scope_rule: 'Only MCP calls whose observed thread_id equals task.manifest.thread_id are primary. Other and unscoped calls remain separate.' };
}
function sessionFromTask(task, replicate, experiment, observationFile, index, labels, prompt) {
  const events = task.evidence.transcript_present ? jsonLines(task.evidence.transcript) : [];
  const starts = events.filter(e => e.direction === 'send' && e.message?.method === 'turn/start' && e.message.params?.threadId === task.primary_thread_id);
  ensure(starts.length <= 1 && (task.manifest.execution_started !== true || starts.length === 1), `Primary submission count is not one: ${replicate}/${task.id}`);
  const submitted = starts[0]?.message.params.input;
  const submittedText = Array.isArray(submitted) && submitted.length === 1 && submitted[0].type === 'text' ? submitted[0].text : null;
  return { cohort: 'codex', experiment, task_id: task.id, replicate, session_key: `${replicate}/${task.id}`, observation_file: observationFile, observation_json_pointer: `/tasks/${index}`,
    evidence: task.evidence, primary_thread_id: task.primary_thread_id, primary_scope_certain: task.primary_scope_certain,
    execution_started: task.manifest.execution_started === true, result_status: task.status, model: task.manifest.model ?? null, manifest: task.manifest,
    prompt_submission: { count: starts.length, exact_frozen_prompt_match: submittedText === null ? null : submittedText === prompt, events: starts.map(e => ({ event_sequence: e.sequence, transcript_line: e.line_number })) },
    skillfetch_called: task.skillfetch_called, searched: task.search_calls.length > 0, outer_user_turn_index: task.outer_user_turn_index, first_call: task.first_call,
    skillfetch_call_count: task.skillfetch_call_count, skillfetch_call_attempt_count: task.skillfetch_call_attempt_count, approval_denied_call_count: task.approval_denied_call_count,
    server_result_count: task.server_result_count, successful_server_call_count: task.successful_server_call_count,
    call_summaries: task.calls.map(c => ({ id: c.id, tool: c.tool, thread_id: c.thread_id, event_sequence: c.event_sequence, transcript_line: c.transcript_line, status: c.status, error: c.error,
      protocol_status: c.protocol_status, protocol_success: c.protocol_success, server_result_received: c.server_result_received, server_success_observed: c.server_success_observed, approval_denied: c.approval_denied })),
    search_calls: task.search_calls, load_calls: task.load_calls, raw_load_return_occurrences: task.load_calls.flatMap(c => c.returned_skill_ids || []),
    confirmed_returned_skill_ids: task.confirmed_returned_skill_ids, nonprimary_thread_observations: task.nonprimary_thread_observations, unscoped_thread_observations: task.unscoped_thread_observations,
    no_load_evidence: task.no_load_evidence, turn_end_events: task.turn_end_events, process_exit_events: task.process_exit_events, warnings: task.warnings,
    ...joinLabels(task.id, task.returned_skill_ids, labels) };
}

function extractExperiment(options) {
  const root = fs.realpathSync(options.runRoot), label = readLabelBasis(options.labelBasis);
  const directories = REPLICATES.map(r => fs.realpathSync(options.runDirs?.[r] || path.join(root, r)));
  ensure(unique(directories).length === 3 && directories.every(d => inside(root, d)), 'Three distinct replicate directories must be inside the new root');
  const runs = REPLICATES.map((replicate, i) => {
    const manifestFile = path.join(directories[i], 'manifest.json'), manifest = readJson(manifestFile);
    ensure(['COMPLETED', 'COMPLETED_WITH_FAILURES'].includes(manifest.status) && typeof manifest.finished_at === 'string', `Replicate is not terminal/finished: ${replicate}`);
    const observed = scopeRun(extractRun(directories[i]));
    ensure(observed.frozen_tasks.status === 'VERIFIED' && sameIds(observed.tasks.map(t => t.id), label.rows.keys()), `Frozen task file/IDs are unverified: ${replicate}`);
    const file = path.join(directories[i], 'observations-e2e4.json'), value = { ...observed, experiment_replicate: replicate };
    const bytes = `${JSON.stringify(value, null, 2)}\n`;
    return { replicate, directory: directories[i], manifest: info(manifestFile), file, bytes, observations_sha256: sha256(bytes), observed };
  });
  for (const run of runs) for (const key of [...FIXED_KEYS, 'agents_sha256']) ensure(isDeepStrictEqual(run.observed.manifest[key], runs[0].observed.manifest[key]), `Replicate configuration differs: ${key}`);
  for (const key of FIXED_KEYS.slice(0, 6)) ensure(runs[0].observed.manifest[key] !== undefined, `Missing fixed configuration: ${key}`);
  const frozen = jsonLines(path.join(directories[0], 'tasks.jsonl')), prompts = new Map(frozen.map(t => [t.id, t.prompt]));
  const requestLengths = frozen.map(t => ({ task_id: t.id, characters: [...t.prompt].length, utf16_code_units: t.prompt.length, utf8_bytes: Buffer.byteLength(t.prompt), at_least_800: [...t.prompt].length >= 800, prompt_sha256: sha256(t.prompt), frozen_task_line: t.line_number }));
  const sbp = runs.flatMap(run => run.observed.tasks.map((task, i) => { ensure(task.frozen_prompt.status === 'VERIFIED', `Unverified prompt: ${task.id}`); return sessionFromTask(task, run.replicate, 'e2e4', run.file, i, label.rows, prompts.get(task.id)); }));
  const baselineFile = options.baselineFile || BASELINE_FILE, baseline = readJson(baselineFile);
  ensure(info(baselineFile).sha256 === (options.baselineExpectedSha256 || BASELINE_SHA256), 'E2E3 baseline snapshot SHA256 differs from the frozen source');
  ensure(baseline.sources.runs.length === 3, 'E2E3 must have three recorded source runs');
  const baselineRuns = REPLICATES.map(replicate => {
    const descriptor = baseline.sources.runs.find(r => r.replicate === replicate); ensure(descriptor, `Missing E2E3 replicate ${replicate}`);
    ensure(info(descriptor.observations_file).sha256 === descriptor.observations_sha256, `E2E3 per-run observation SHA256 mismatch: ${replicate}`);
    const observed = scopeRun(readJson(descriptor.observations_file));
    ensure(observed.frozen_tasks.actual_sha256 === runs[0].observed.frozen_tasks.actual_sha256, 'E2E3 and E2E4 task bytes differ');
    for (const key of FIXED_KEYS) ensure(isDeepStrictEqual(observed.manifest[key], runs[0].observed.manifest[key]), `E2E3/E2E4 fixed condition differs: ${key}`);
    return { replicate, descriptor, observed };
  });
  const s0 = baselineRuns.flatMap(run => run.observed.tasks.map((task, i) => sessionFromTask(task, run.replicate, 'e2e3', run.descriptor.observations_file, i, label.rows, prompts.get(task.id))));
  for (const sessions of [sbp, s0]) {
    ensure(sessions.length === 57 && unique(sessions.map(s => s.session_key)).length === 57, 'Expected 57 unique task/replicate observations');
    for (const rep of REPLICATES) ensure(sameIds(sessions.filter(s => s.replicate === rep).map(s => s.task_id), label.rows.keys()), `Incomplete task matrix: ${rep}`);
    const threads = sessions.filter(s => s.execution_started).map(s => s.primary_thread_id); ensure(threads.every(t => typeof t === 'string') && unique(threads).length === threads.length, 'Missing or reused primary thread ID');
  }
  const cell = s => ({ session_key: s.session_key, loaded_skill_ids: s.loaded_skill_ids, raw_load_return_occurrences: s.raw_load_return_occurrences, relevance_counts: s.relevance_counts,
    oracle_matches: s.oracle_matches, hit_status: s.hit_status, result_status: s.result_status, query_check_statuses: s.search_calls.map(c => c.query_check_status),
    first_call: s.first_call, no_load_status: s.no_load_evidence.status, explicit_none_confirmed: s.no_load_evidence.explicit_none_confirmed });
  const taskSets = requestLengths.map(length => ({ ...length, oracle_related: label.provenance.related_task_ids.includes(length.task_id),
    e2e4: Object.fromEntries(REPLICATES.map(r => [r, cell(sbp.find(s => s.task_id === length.task_id && s.replicate === r))])),
    e2e3: Object.fromEntries(REPLICATES.map(r => [r, cell(s0.find(s => s.task_id === length.task_id && s.replicate === r))])) }));
  const combined = { schema_version: 4, generated_at: new Date().toISOString(), analysis_type: 'OFFLINE_EXISTING_RECORDINGS', run_root: root,
    sources: { extractor: info(__filename), reused_raw_parser: info(path.join(__dirname, 'codex-e2e-2-extract.cjs')), reused_label_and_metric_helpers: info(path.join(__dirname, 'codex-e2e-3-extract.cjs')),
      e2e3: info(baselineFile), e2e3_runs: baselineRuns.map(r => r.descriptor),
      runs: runs.map(r => ({ replicate: r.replicate, run_directory: r.directory, manifest: r.manifest, observations_file: r.file, observations_sha256: r.observations_sha256, frozen_tasks: r.observed.frozen_tasks })) },
    label_basis: label.provenance, fixed_condition_keys_checked: FIXED_KEYS,
    agents_sha256: { e2e4: runs[0].observed.manifest.agents_sha256, e2e3: baselineRuns[0].observed.manifest.agents_sha256 },
    units: { ...runs[0].observed.units,
      primary_thread: 'Primary metrics include only explicit MCP thread IDs matching each task manifest. Other-thread and unscoped MCP evidence is retained separately.',
      primary_hit: 'Confirmed observed relevant-return sessions / ALL selected related-task sessions (51 pooled), including zero-load selections and uncertain return evidence. Loaded-related hit is secondary.',
      mean_returned_ids: 'Sum of distinct returned full skill IDs within each session / all 57 selected sessions. Known zero-load sessions contribute zero; ambiguous return sets make the exact mean null, with a separate observed lower bound.',
      explicit_none: 'No automatic intent classification. Zero loads, failed calls, successful empty skills arrays, empty selection arguments, and assistant excerpts remain separate evidence for manual review.',
      precision: 'Micro R/(R+N); macro mean of per-session R/(R+N) among sessions with at least one graded ID. All unknown grades remain null and are counted separately.',
      metric_ids: 'Exact full returned IDs, unique within a session. No request/resolve candidates, error-entry IDs, basename normalization, or invented grades.',
      baseline: 'All 57 existing E2E3 sessions remain in S0. Labels and denominators are recomputed using the same functions; no session is excluded.' },
    limitations: [...runs[0].observed.limitations, 'Explicit-none review has not been performed by this extractor. No task-result or code-quality grades are assigned.'],
    request_lengths: requestLengths, long_request_task_ids: requestLengths.filter(r => r.at_least_800).map(r => r.task_id),
    sessions: { e2e4: sbp, e2e3: s0 }, metrics: { e2e4: cohortMetrics(sbp), e2e3: cohortMetrics(s0) }, task_sets: taskSets,
    warnings: [...sbp, ...s0].flatMap(s => s.warnings.map(warning => ({ experiment: s.experiment, session_key: s.session_key, warning }))) };
  return { combined, perRuns: runs };
}
function parseArgs(argv) {
  if (argv.length === 1 && ['--help', '-h'].includes(argv[0])) return { help: true };
  const args = {};
  for (let i = 0; i < argv.length; i += 2) {
    ensure(['--run-root', '--r1-dir', '--r2-dir', '--r3-dir', '--out'].includes(argv[i]) && !args[argv[i]] && argv[i + 1] && !argv[i + 1].startsWith('--'), `Invalid argument: ${argv[i]}`);
    args[argv[i]] = path.resolve(argv[i + 1]);
  }
  ensure(args['--run-root'], HELP.trim());
  return { runRoot: args['--run-root'], runDirs: Object.fromEntries(REPLICATES.map(r => [r, args[`--${r}-dir`] || path.join(args['--run-root'], r)])), out: args['--out'] || path.join(args['--run-root'], 'observations-e2e4.json') };
}
module.exports = { aggregateMetrics, cohortMetrics, primaryThreadTask, extractExperiment, writeExperiment, parseArgs };
if (require.main === module) {
  try { const options = parseArgs(process.argv.slice(2)); if (options.help) process.stdout.write(HELP); else process.stdout.write(`${JSON.stringify(writeExperiment(extractExperiment(options), options), null, 2)}\n`); }
  catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
}
