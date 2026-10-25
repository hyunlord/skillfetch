#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { isDeepStrictEqual } = require('node:util');
const ACTION_TYPES = new Set(['commandExecution', 'fileChange', 'mcpToolCall', 'dynamicToolCall', 'collabAgentToolCall', 'webSearch', 'imageView', 'sleep', 'imageGeneration']);
const HELP = 'Usage: node codex-e2e-extract.cjs --run-dir DIR [--additional-run-dir DIR] --out FILE\nReads local runner artifacts only; never launches Codex or calls tools.\n';
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const present = value => value === undefined ? null : value;
const unique = values => [...new Set(values)];

function readJson(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }

function parseArgs(argv) {
  if (argv.length === 1 && ['--help', '-h'].includes(argv[0])) return { help: true };
  const options = {};
  for (let i = 0; i < argv.length; i += 2) {
    const name = argv[i];
    if (!['--run-dir', '--additional-run-dir', '--out'].includes(name) || options[name] || !argv[i + 1] || argv[i + 1].startsWith('--')) throw new Error(`Invalid argument: ${name}`);
    options[name] = path.resolve(argv[i + 1]);
  }
  if (!options['--run-dir'] || !options['--out']) throw new Error(HELP.trim());
  return options;
}

function readTranscript(file, warnings) {
  if (!fs.existsSync(file)) { warnings.push('Transcript is absent; zero observed calls does not establish that no call occurred.'); return []; }
  let previous = 0;
  return fs.readFileSync(file, 'utf8').split(/\r?\n/).flatMap((line, index) => {
    if (!line.trim()) return [];
    try {
      const event = JSON.parse(line);
      if (!object(event) || !Number.isSafeInteger(event.sequence) || event.sequence <= previous) throw new Error('Missing or non-increasing event sequence');
      if (event.sequence !== previous + 1) warnings.push(`Transcript sequence gap before event ${event.sequence}; raw response-cycle ordinals are not reliable.`);
      previous = event.sequence;
      return [{ ...event, line_number: index + 1 }];
    } catch (error) { warnings.push(`Transcript line ${index + 1}: ${error.message}`); return []; }
  });
}

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

function collectCalls(events, warnings) {
  const calls = new Map();
  const actions = new Set();
  const items = new Set();
  for (const event of events) {
    if (event.direction !== 'receive' || !['item/started', 'item/completed'].includes(event.message?.method)) continue;
    const params = event.message.params;
    const item = params?.item;
    if (!object(item) || typeof item.id !== 'string') continue;
    items.add(item.id);
    if (ACTION_TYPES.has(item.type)) actions.add(item.id);
    if (item.type !== 'mcpToolCall' || item.server !== 'skillfetch') continue;
    if (!calls.has(item.id)) calls.set(item.id, {
      id: item.id, tool: present(item.tool), thread_id: present(params.threadId), turn_id: present(params.turnId),
      event_sequence: event.sequence, transcript_line: event.line_number, at: present(event.at), action_ordinal: actions.size, item_ordinal: items.size,
      status: null, error: null, failed: false, started: false, completed: false, argument_observations: [], result_observations: [], event_sequences: [],
    });
    const call = calls.get(item.id);
    if (call.tool !== item.tool || call.thread_id !== present(params.threadId) || call.turn_id !== present(params.turnId)) warnings.push(`MCP item ID ${item.id} has conflicting identity fields.`);
    call.event_sequences.push(event.sequence);
    call.started ||= event.message.method === 'item/started';
    call.completed ||= event.message.method === 'item/completed';
    if (Object.hasOwn(item, 'status')) call.status = item.status;
    if (item.error != null) call.error = item.error;
    call.failed ||= item.status === 'failed' || item.error != null || item.result?.isError === true;
    if (Object.hasOwn(item, 'arguments') && !call.argument_observations.some(observation => JSON.stringify(observation.arguments) === JSON.stringify(item.arguments))) {
      call.argument_observations.push({ event_sequence: event.sequence, arguments: item.arguments });
    }
    if (item.result != null && !call.result_observations.some(observation => JSON.stringify(observation.result) === JSON.stringify(item.result))) {
      call.result_observations.push({ event_sequence: event.sequence, result: item.result });
    }
  }
  return [...calls.values()].map(call => ({ ...call,
    approval_denied: call.error?.message === 'MCP tool call requires approval, but approval policy is never',
    server_result_received: call.result_observations.length > 0,
    server_success_observed: call.completed && call.status === 'completed' && !call.failed && call.result_observations.length > 0 }));
}

function searchCall(call) {
  const observations = call.argument_observations.map(observation => {
    let parsed = observation.arguments;
    let parseError = null;
    if (typeof parsed === 'string') {
      try { parsed = JSON.parse(parsed); } catch (error) { parsed = null; parseError = error.message; }
    }
    const args = object(parsed) ? parsed : {};
    return { ...observation, parsed_arguments: object(parsed) ? parsed : null, parse_error: parseError,
      queries: present(args.queries), query_legacy: present(args.query),
      query_argument_kind: Object.hasOwn(args, 'queries') ? (Object.hasOwn(args, 'query') ? 'both' : 'queries') : (Object.hasOwn(args, 'query') ? 'query_legacy' : 'absent') };
  });
  return { id: call.id, event_sequence: call.event_sequence, status: call.status, failed: call.failed,
    arguments: observations[0]?.arguments ?? null, queries: observations[0]?.queries ?? null, query_legacy: observations[0]?.query_legacy ?? null,
    argument_observations: observations };
}

function loadCall(call) {
  const evidence = [];
  const errors = [];
  const payloads = [];
  for (const observation of call.result_observations) {
    const result = observation.result;
    if (!object(result)) continue;
    if (object(result.structuredContent)) payloads.push({ source: 'structuredContent', event_sequence: observation.event_sequence, payload: result.structuredContent });
    for (const [index, content] of (Array.isArray(result.content) ? result.content : []).entries()) {
      if (content?.type !== 'text' || typeof content.text !== 'string') continue;
      try { payloads.push({ source: `content[${index}].text JSON`, event_sequence: observation.event_sequence, payload: JSON.parse(content.text) }); }
      catch { /* Non-JSON text remains available in the original transcript. */ }
    }
  }
  for (const { source, event_sequence, payload } of payloads) {
    if (!object(payload)) continue;
    if (Array.isArray(payload.skills)) evidence.push({ source, event_sequence,
      ids: payload.skills.filter(skill => object(skill) && typeof skill.id === 'string').map(skill => skill.id),
      unrecognized_skill_entries: payload.skills.filter(skill => !object(skill) || typeof skill.id !== 'string') });
    if (Object.hasOwn(payload, 'error') || Object.hasOwn(payload, 'errors')) errors.push({ source, event_sequence, error: present(payload.error), errors: present(payload.errors) });
  }
  return { id: call.id, event_sequence: call.event_sequence, status: call.status, failed: call.failed, error: call.error,
    returned_skill_ids: evidence.length ? unique(evidence.flatMap(item => item.ids)) : null, returned_skill_evidence: evidence, payload_errors: errors };
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

function extractTask(root, record) {
  const directory = path.join(root, 'tasks', record.id);
  const taskFile = path.join(directory, 'task.json');
  const task = fs.existsSync(taskFile) ? readJson(taskFile) : record;
  if (!object(task) || task.id !== record.id) throw new Error(`Task manifest ID mismatch: ${record.id}`);
  const warnings = [];
  const transcript = path.join(directory, 'transcript.jsonl');
  const events = readTranscript(transcript, warnings);
  const raw = responseCycles(events, warnings);
  const calls = collectCalls(events, warnings);
  const loads = calls.filter(call => call.tool === 'load_skills').map(loadCall);
  return { id: record.id, repo: present(task.repo), status: present(task.status), manifest: task,
    root_manifest_disagreements: Object.keys(task).filter(key => Object.hasOwn(record, key) && JSON.stringify(task[key]) !== JSON.stringify(record[key])),
    evidence: { task_manifest: fs.existsSync(taskFile) ? taskFile : path.join(root, 'manifest.json'), transcript,
      transcript_present: fs.existsSync(transcript), parsed_event_count: events.length },
    outer_user_turn_index: task.execution_started === true ? 1 : null,
    skillfetch_called: calls.length > 0, skillfetch_call_count: calls.length, skillfetch_call_attempt_count: calls.length,
    approval_denied_call_count: calls.filter(call => call.approval_denied).length,
    server_result_count: calls.filter(call => call.server_result_received).length,
    successful_server_call_count: calls.filter(call => call.server_success_observed).length,
    first_call: firstCall(calls[0], raw, warnings),
    calls: calls.map(({ result_observations, ...call }) => ({ ...call, result_event_sequences: result_observations.map(item => item.event_sequence) })),
    search_calls: calls.filter(call => call.tool === 'search_skills').map(searchCall), load_calls: loads,
    returned_skill_ids: unique(loads.flatMap(call => call.returned_skill_ids || [])),
    raw_response_methods: raw.methods, observed_completed_model_responses: raw.completed_response_count,
    turn_start_request_event_sequences: events.filter(event => event.direction === 'send' && event.message?.method === 'turn/start').map(event => event.sequence),
    turn_end_events: events.filter(event => event.direction === 'receive' && event.message?.method === 'turn/completed').map(event => ({ event_sequence: event.sequence, turn: event.message.params?.turn ?? null })),
    process_exit_events: events.filter(event => event.direction === 'process-exit'), warnings: unique(warnings) };
}

function validateTaskIds(tasks, label) {
  if (!Array.isArray(tasks) || new Set(tasks.map(task => task?.id)).size !== tasks.length || tasks.some(task => typeof task?.id !== 'string' || !/^[A-Za-z0-9_-]+$/.test(task.id))) throw new Error(`${label} must contain unique safe task IDs`);
}

function combineAttempts(primary, additional) {
  const replacements = new Map(additional?.tasks.map(task => [task.id, task]) || []);
  for (const task of replacements.values()) if (!primary.tasks.some(original => original.id === task.id)) throw new Error(`Unknown additional task ID: ${task.id}`);
  return primary.tasks.map(original => {
    const replacement = replacements.get(original.id);
    const attempts = [{ source_run: primary.root, ...original }];
    if (replacement) {
      if (original.manifest.status !== 'NOT_RUN' || original.manifest.execution_started !== false || original.manifest.turn_start_requested !== false || original.turn_start_request_event_sequences.length || original.calls.length || original.turn_end_events.length) throw new Error(`Refusing duplicate or uncertain submission: ${original.id} was already submitted`);
      if (typeof original.manifest.prompt_sha256 !== 'string' || replacement.manifest.prompt_sha256 !== original.manifest.prompt_sha256) throw new Error(`Mismatched prompt_sha256: ${original.id}`);
      attempts.push({ source_run: additional.root, ...replacement });
    }
    if (attempts.some(attempt => attempt.turn_start_request_event_sequences.length > 1)) throw new Error(`Duplicate turn/start submissions: ${original.id}`);
    const chosen = replacement?.manifest.execution_started === true ? attempts[1] : attempts[0];
    return { ...chosen, chosen_source_run: chosen.source_run, attempts: attempts.map(attempt => ({ source_run: attempt.source_run,
      manifest: attempt.manifest, evidence: attempt.evidence, turn_start_request_event_sequences: attempt.turn_start_request_event_sequences,
      observed_call_attempt_count: attempt.skillfetch_call_attempt_count, warnings: attempt.warnings })) };
  });
}

function extractRun(root, additionalRoot = null) {
  const manifest = readJson(path.join(root, 'manifest.json'));
  validateTaskIds(manifest.tasks, 'Primary manifest');
  if (manifest.tasks.length !== 19) throw new Error('Primary runner manifest must contain exactly 19 tasks');
  const additionalManifest = additionalRoot ? readJson(path.join(additionalRoot, 'manifest.json')) : null;
  if (additionalManifest) {
    validateTaskIds(additionalManifest.tasks, 'Additional manifest');
    for (const key of ['source_commit', 'codex_version', 'tasks_sha256', 'config_sha256', 'agents_sha256', 'cloud_skills_sha256', 'repository_refs']) {
      if (manifest[key] === undefined || !isDeepStrictEqual(manifest[key], additionalManifest[key])) throw new Error(`Additional run differs in ${key}`);
    }
  }
  const tasks = combineAttempts({ root, tasks: manifest.tasks.map(task => extractTask(root, task)) }, additionalManifest && { root: additionalRoot, tasks: additionalManifest.tasks.map(task => extractTask(additionalRoot, task)) });
  const { tasks: omitted, ...runManifest } = manifest;
  return { schema_version: 1, run_directory: root, additional_run_directory: additionalRoot, source_evidence_kind: manifest.evidence_kind ?? null,
    manifest: runManifest, additional_manifest: additionalManifest,
    units: { first_call_model_response_cycle: 'One-based ordinal of unique rawResponse/completed responseId boundaries within the matching thread/turn; mapping uses a direct call ID or an explicitly labeled unique closed exec interval inference.',
      skillfetch_called: 'An observed model MCP invocation attempt, including calls blocked before server execution by approval policy.',
      successful_server_call: 'An observed completed MCP lifecycle with status completed, a non-null server result and no protocol-level failure; this does not assess task-result correctness.',
      outer_user_turn_index: 'One only when execution_started is true in the task manifest; independent of model response cycles.',
      action_ordinal: 'First-seen ordinal among distinct actionable item IDs in item/started or item/completed events.',
      item_ordinal: 'First-seen ordinal among all distinct item IDs in item/started or item/completed events.',
      stage4_comparison: 'Stage4 assistant-message counts are a different unit and are not directly equated to model-response cycles or outer user turns.' },
    limitations: ['Counts describe observed skillfetch MCP lifecycle events, deduplicated by item.id; absence of evidence is not evidence of absence in incomplete transcripts.',
      'Returned skill IDs come only from result.structuredContent.skills or JSON text result.content[].text skills arrays; requested IDs, resolver candidates and error IDs are excluded.',
      'Legacy raw-event payloads and code-mode parent-call relationships are not inferred without an observed/schema-supported causal mapping.'],
    totals: { task_count: tasks.length, execution_started_count: tasks.filter(task => task.manifest.execution_started === true).length,
      skillfetch_called_count: tasks.filter(task => task.skillfetch_called).length, skillfetch_call_count: tasks.reduce((total, task) => total + task.skillfetch_call_count, 0),
      approval_denied_call_count: tasks.reduce((total, task) => total + task.approval_denied_call_count, 0),
      server_result_count: tasks.reduce((total, task) => total + task.server_result_count, 0), successful_server_call_count: tasks.reduce((total, task) => total + task.successful_server_call_count, 0),
      task_status_counts: Object.fromEntries(unique(tasks.map(task => task.status)).map(status => [status, tasks.filter(task => task.status === status).length])),
      tasks_with_observable_first_call_cycle: tasks.filter(task => task.first_call?.model_response_cycle != null).length }, tasks };
}

function main(argv) {
  const options = parseArgs(argv);
  if (options.help) { process.stdout.write(HELP); return; }
  const root = fs.realpathSync(options['--run-dir']);
  const output = options['--out'];
  if (fs.existsSync(output)) throw new Error('Output already exists; refusing to overwrite evidence');
  const summary = extractRun(root, options['--additional-run-dir'] ? fs.realpathSync(options['--additional-run-dir']) : null);
  fs.writeFileSync(output, `${JSON.stringify(summary, null, 2)}\n`, { flag: 'wx', mode: 0o600 });
  process.stdout.write(`${output}\n`);
}

module.exports = { parseArgs, extractRun };
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
}
