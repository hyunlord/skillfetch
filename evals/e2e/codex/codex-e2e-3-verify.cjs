#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const { isDeepStrictEqual: equal } = require('node:util');

const E2E = __dirname;
const OLD = path.join(E2E, 'codex-e2e-runs/20261024-subscription-mcp-approved-14d2020');
const FIRST = path.join(E2E, 'codex-e2e-runs/20261023-subscription-14d2020');
const SOURCE_COMMIT = '14d2020f1275e10a272eb46575c9bd6d4a2182e4';
const REPORT_SHA = 'db5b22600f4d20048f5669a39221335d8b5f7106cd1824d4b2deb57848d139c5';
const SECOND_REPORT_SHA = 'bc8e4d41b17785b3408c5cb62519d55dd32d77751eaedc751d32d019e437effc';
const OLD_CONFIG_SHA = '69fb11307213035fce1442078304ff1891a1b4b22e5254a75d9387884bb590e1';
const AGENTS_SHA = '4cdfac9064f4f6dda0846dff9c8fe52a90dd2e65ba09cc494c735ea9c83bfa8a';
const AGENTS_SOURCE = path.join(E2E, 'codex-e2e-3-preparation/AGENTS.md');
const REPLICATES = ['r1', 'r2', 'r3'];
const API_KEYS = ['OPENAI_API_KEY', 'CODEX_API_KEY', 'AZURE_OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY', 'GEMINI_API_KEY', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'];
const ENV_KEYS = new Set(['PATH', 'HOME', 'CODEX_HOME', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM']);
const TOOLS = ['profile_repo', 'search_skills', 'resolve_set', 'load_skills'];
const CONTROLLER_METHODS = new Set(['initialize', 'initialized', 'account/read', 'thread/start', 'mcpServerStatus/list', 'turn/start', 'turn/interrupt']);
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const bytes = file => fs.readFileSync(file);
const read = file => JSON.parse(bytes(file));
const lines = file => bytes(file).toString('utf8').split(/\r?\n/).filter(line => line.trim()).map(JSON.parse);
const normalizedPath = value => path.resolve(value).replace(/^\/private\/(var|tmp)\//, '/$1/');

function absent(file) {
  try { fs.lstatSync(file); return false; }
  catch (error) { if (error.code === 'ENOENT') return true; throw error; }
}

function finalConfigMatches(oldInput, newInput, oldFinal, newFinal, repoPath) {
  const trust = `\n[projects.${JSON.stringify(repoPath)}]\ntrust_level = "trusted"\n`;
  return oldInput === newInput && oldFinal === oldInput + trust && newFinal === newInput + trust && oldFinal === newFinal;
}

function compareParsedPolicies(oldConfig, newConfig) {
  const program = [
    'import json, sys, tomllib',
    'old_text, new_text = json.load(sys.stdin)',
    'old, new = tomllib.loads(old_text), tomllib.loads(new_text)',
    'def policy(config):',
    '    return {"approval_policy": config.get("approval_policy"), "sandbox_mode": config.get("sandbox_mode"), "network_access": config.get("sandbox_workspace_write", {}).get("network_access"), "model": config.get("model"), "reasoning_effort": config.get("model_reasoning_effort"), "forced_login_method": config.get("forced_login_method"), "mcp_servers": sorted(config.get("mcp_servers", {})), "skillfetch_approval": config.get("mcp_servers", {}).get("skillfetch", {}).get("default_tools_approval_mode"), "projects": config.get("projects", {})}',
    'old_policy, new_policy = policy(old), policy(new)',
    'print(json.dumps({"old": old_policy, "new": new_policy, "policies_equal": old == new}))',
  ].join('\n');
  const result = cp.spawnSync('python3', ['-I', '-c', program], { input: JSON.stringify([oldConfig, newConfig]), encoding: 'utf8', timeout: 30000, maxBuffer: 1024 * 1024 });
  if (result.error || result.status !== 0) throw new Error('Isolated standard-library TOML policy parse failed');
  return JSON.parse(result.stdout);
}

function transcriptFacts(events) {
  const sent = method => events.filter(event => event.direction === 'send' && event.message?.method === method);
  const received = method => events.filter(event => event.direction === 'receive' && event.message?.method === method);
  const interactive = events.filter(event => event.direction === 'receive' && event.message?.id !== undefined && typeof event.message?.method === 'string');
  const mcp = events.filter(event => event.direction === 'receive' && ['item/started', 'item/completed'].includes(event.message?.method) && event.message?.params?.item?.type === 'mcpToolCall');
  return {
    ordered: events.length > 0 && events.every((event, index) => event.sequence === index + 1),
    sent, received, interactive, mcp,
    resumed: events.filter(event => event.direction === 'send' && ['thread/resume', 'thread/fork', 'turn/steer'].includes(event.message?.method)),
    controllerToolCalls: events.filter(event => event.direction === 'send' && /^(?:tools\/call|mcp.*\/call|item\/tool\/call)$/i.test(event.message?.method || '')),
    unexpectedControllerMethods: events.filter(event => event.direction === 'send' && typeof event.message?.method === 'string' && !CONTROLLER_METHODS.has(event.message.method)),
    exits: events.filter(event => event.direction === 'process-exit'),
  };
}

function appliedAgentsValid(applied, worktree, agentsBytes, submittedAt) {
  return applied.path === path.join(worktree, 'AGENTS.md') && applied.sha256 === AGENTS_SHA &&
    applied.input_sha256 === AGENTS_SHA && applied.bytes === agentsBytes.length && applied.phase === 'before_turn_start' &&
    Array.isArray(applied.checks) && applied.checks.length === 2 &&
    equal(applied.checks.map(item => item.phase), ['after_copy', 'before_turn_start']) &&
    applied.checks.every(item => item.path === applied.path && item.sha256 === AGENTS_SHA && item.bytes === agentsBytes.length && Number.isFinite(Date.parse(item.checked_at))) &&
    Date.parse(applied.checks[0].checked_at) <= Date.parse(applied.checks[1].checked_at) &&
    applied.checked_at === applied.checks[1].checked_at && Date.parse(applied.checked_at) <= Date.parse(submittedAt);
}

function command(program, args) {
  const result = cp.spawnSync(program, args, { encoding: 'utf8', timeout: 30000, maxBuffer: 1024 * 1024 });
  if (result.error || result.status !== 0) throw new Error('Read-only verification command failed');
  return result.stdout.trim();
}

function verifyReplicate(run, agentsBytes) {
  const manifestBytes = bytes(path.join(run, 'manifest.json'));
  const manifest = JSON.parse(manifestBytes);
  if (manifest.status === 'RUNNING' || !manifest.finished_at) {
    throw new Error('Refusing final audit before the runner manifest is finished');
  }
  const checks = [];
  const check = (name, passed, evidence = {}) => checks.push({ name, status: passed === true ? 'PASS' : 'FAIL', ...evidence });
  const old = read(path.join(OLD, 'manifest.json'));
  const priorManifests = [old, read(path.join(FIRST, 'manifest.json')), read(path.join(`${FIRST}-unsubmitted`, 'manifest.json'))];
  const priorThreads = new Set(priorManifests.flatMap(m => m.tasks.map(task => task.thread_id).filter(Boolean)));
  const priorTurns = new Set(priorManifests.flatMap(m => m.tasks.map(task => task.turn_id).filter(Boolean)));
  const observedRows = lines(path.join(run, 'tasks.jsonl'));
  const oldRows = lines(path.join(OLD, 'tasks.jsonl'));
  const rows = oldRows;
  const preflight = read(path.join(run, 'source-preflight.json'));
  const config = bytes(path.join(run, 'config.input.toml'));
  const oldConfig = bytes(path.join(OLD, 'config.input.toml'));
  check('nineteen_unique_exact_inputs', observedRows.length === 19 && new Set(observedRows.map(row => row.id)).size === 19 && new Set(observedRows.map(row => row.prompt)).size === 19 && equal(observedRows, oldRows), { count: observedRows.length });
  check('manifest_task_identities', manifest.tasks.length === 19 && equal(manifest.tasks.map(task => ({ id: task.id, repo: task.repo, prompt_sha256: task.prompt_sha256 })), rows.map(row => ({ id: row.id, repo: row.repo, prompt_sha256: sha(row.prompt) }))));
  check('exactly_nineteen_task_directories', equal(fs.readdirSync(path.join(run, 'tasks')).filter(name => fs.statSync(path.join(run, 'tasks', name)).isDirectory()).sort(), rows.map(row => row.id).sort()));
  for (const [file, key] of [['tasks.jsonl', 'tasks_sha256'], ['cloud-skills.input.json', 'cloud_skills_sha256']]) {
    const current = bytes(path.join(run, file));
    check(`unchanged_${file}`, current.equals(bytes(path.join(OLD, file))) && sha(current) === manifest[key] && manifest[key] === old[key], { sha256: sha(current) });
  }
  check('full_agents_matches_controlled_source', bytes(path.join(run, 'AGENTS.input.md')).equals(agentsBytes) && sha(agentsBytes) === AGENTS_SHA && manifest.agents_sha256 === AGENTS_SHA, { sha256: sha(agentsBytes), source_path: AGENTS_SOURCE });
  check('current_stage5_tasks_unchanged', bytes(path.join(run, 'tasks.jsonl')).equals(bytes(path.join(E2E, 'stage5/tasks.jsonl'))));
  check('source_preflight_unchanged', bytes(path.join(run, 'source-preflight.json')).equals(bytes(path.join(OLD, 'source-preflight.json'))) && preflight.status === 'PASS' && preflight.source_commit === SOURCE_COMMIT && manifest.source_commit === SOURCE_COMMIT);
  for (const [kind, count] of [['source', 238], ['index', 6]]) {
    const entries = Object.entries(preflight[`${kind}_files`]);
    const root = fs.realpathSync(preflight[`${kind}_path`]);
    const mismatches = [];
    for (const [relative, expected] of entries) {
      if (path.isAbsolute(relative) || relative.split(/[\\/]/).includes('..')) { mismatches.push(relative); continue; }
      try {
        const file = fs.realpathSync(path.join(root, relative));
        if (!file.startsWith(`${root}${path.sep}`) || sha(bytes(file)) !== expected) mismatches.push(relative);
      } catch { mismatches.push(relative); }
    }
    check(`${kind}_hashes`, entries.length === count && mismatches.length === 0, { checked_files: entries.length, mismatches });
  }
  check('config_exactly_matches_e2e2', sha(oldConfig) === OLD_CONFIG_SHA && config.equals(oldConfig) && sha(config) === manifest.config_sha256, { old_sha256: sha(oldConfig), new_sha256: sha(config) });
  check('cloud_skills_empty', equal(read(path.join(run, 'cloud-skills.input.json')).skills, []));
  check('run_controls_unchanged', manifest.concurrency === old.concurrency && manifest.timeout_seconds === old.timeout_seconds && manifest.assistant_round_cap === null && manifest.experimental_raw_events_requested === true && manifest.recovery_of === null && !manifest.runner_errors?.length, { concurrency: manifest.concurrency, timeout_seconds: manifest.timeout_seconds });
  check('requested_identity', manifest.requested_model === 'gpt-6-astra' && equal(manifest.repository_refs, old.repository_refs) && manifest.mcp_approval_config?.default_tools_approval_mode === 'approve');
  const cliVersion = command('/opt/homebrew/bin/codex', ['--version']);
  check('cli_version_unchanged', cliVersion === 'codex-cli 0.164.0' && manifest.codex_version === cliVersion && old.codex_version === cliVersion, { cli_version: cliVersion });
  const worktrees = {};
  for (const repo of ['fastapi', 'nextjs']) {
    const repoPath = path.join(E2E, 'repos', repo);
    const ref = command('git', ['-C', repoPath, 'rev-parse', 'refs/heads/s5']);
    worktrees[repo] = command('git', ['-C', repoPath, 'worktree', 'list', '--porcelain', '-z']).split('\0').filter(field => field.startsWith('worktree ')).map(field => normalizedPath(field.slice(9)));
    check(`${repo}_s5_unchanged`, ref === old.repository_refs[repo] && ref === manifest.repository_refs[repo], { commit: ref });
  }
  const threadIds = [];
  const turnIds = [];
  const taskEvidence = [];
  for (const row of rows) {
    const directory = path.join(run, 'tasks', row.id);
    const prefix = `${row.id}:`;
    const taskChecksBefore = checks.length;
    try {
      const task = read(path.join(directory, 'task.json'));
      const events = lines(path.join(directory, 'transcript.jsonl'));
      const facts = transcriptFacts(events);
      const start = read(path.join(directory, 'thread-start.json'));
      const turnStart = read(path.join(directory, 'turn-start.json'));
      const turnEnd = read(path.join(directory, 'turn-completed.json'));
      const account = read(path.join(directory, 'account-read.json'));
      const launch = read(path.join(directory, 'launch.json'));
      const login = read(path.join(directory, 'login-status.json'));
      const approval = read(path.join(directory, 'mcp-get-skillfetch.json'));
      const approvalText = bytes(path.join(directory, 'mcp-get-skillfetch.stdout.txt')).toString('utf8');
      const servers = read(path.join(directory, 'mcp-status.json'));
      const home = path.join(directory, 'home');
      const codexHome = path.join(home, '.codex');
      const expectedWorktree = path.join(manifest.owned_worktree_root, row.id);
      const oldFinalConfigPath = path.join(OLD, 'tasks', row.id, 'home/.codex/config.toml');
      const oldFinalConfig = bytes(oldFinalConfigPath).toString('utf8');
      const finalConfig = bytes(path.join(codexHome, 'config.toml')).toString('utf8');
      threadIds.push(task.thread_id);
      turnIds.push(task.turn_id);
      check(`${prefix}manifest_matches_task`, equal(task, manifest.tasks.find(value => value.id === row.id)));
      check(`${prefix}transcript_order`, facts.ordered, { event_count: events.length });
      check(`${prefix}single_exact_submission`, facts.sent('turn/start').length === 1 && equal(facts.sent('turn/start')[0].message.params, { threadId: task.thread_id, input: [{ type: 'text', text: row.prompt }] }) && facts.resumed.length === 0 && task.turn_start_requested === true && task.execution_started === true);
      check(`${prefix}single_fresh_thread`, facts.sent('thread/start').length === 1 && start.result?.thread?.ephemeral === true && task.thread_id === start.result.thread.id && !priorThreads.has(task.thread_id));
      const request = facts.sent('thread/start')[0]?.message;
      check(`${prefix}thread_policy_requested`, request?.params?.approvalPolicy === 'never' && request.params.sandbox === 'workspace-write' && request.params.ephemeral === true && request.params.cwd === task.worktree);
      check(`${prefix}controller_input_shape_and_repository_instructions_unchanged`, equal(Object.keys(request?.params || {}).sort(), ['approvalPolicy', 'cwd', 'ephemeral', 'experimentalRawEvents', 'model', 'sandbox'].sort()) && equal(read(path.join(directory, 'repository-instructions.json')), read(path.join(OLD, 'tasks', row.id, 'repository-instructions.json'))));
      const applied = read(path.join(directory, 'agents-applied.json'));
      check(`${prefix}full_agents_applied_before_submission`, appliedAgentsValid(applied, task.worktree, agentsBytes, facts.sent('turn/start')[0]?.at), { applied_sha256: applied.sha256, before_turn_start_at: applied.checked_at });
      check(`${prefix}thread_policy_effective`, start.result?.approvalPolicy === 'never' && start.result.sandbox?.type === 'workspaceWrite' && start.result.sandbox.networkAccess === false && equal(start.result.sandbox.writableRoots, []));
      check(`${prefix}actual_model_auth`, task.model === 'gpt-6-astra' && task.reasoning_effort === 'medium' && task.model_provider === 'openai' && task.cli_version === '0.164.0' && start.result.model === task.model && start.result.reasoningEffort === task.reasoning_effort && start.result.modelProvider === task.model_provider && start.result.thread.cliVersion === task.cli_version && task.auth_mode === 'chatgpt' && task.auth_plan_type === 'pro' && account.result?.account?.type === 'chatgpt' && account.result.account.planType === 'pro');
      check(`${prefix}login_subscription_no_api_environment`, login.exit_code === 0 && login.chatgpt === true && login.output === 'Logged in using ChatGPT' && API_KEYS.every(key => login.api_key_environment_absent?.[key] === true) && equal(task.login_status, login));
      check(`${prefix}isolated_launch`, launch.command === '/opt/homebrew/bin/codex' && equal(launch.args, ['app-server', '--stdio', '--strict-config', '--cloud-skills-snapshot', path.join(codexHome, 'cloud-skills.json')]) && launch.cwd === expectedWorktree && launch.cwd === task.worktree && launch.env?.HOME === home && launch.env.CODEX_HOME === codexHome && launch.env.TMPDIR === path.join(directory, 'tmp') && typeof launch.env.PATH === 'string' && Object.keys(launch.env).every(key => ENV_KEYS.has(key)) && API_KEYS.every(key => !Object.hasOwn(launch.env, key)), { env_keys: Object.keys(launch.env || {}).sort() });
      check(`${prefix}config_matches_e2e2_with_baseline_trust`, finalConfigMatches(oldConfig.toString('utf8'), config.toString('utf8'), oldFinalConfig, finalConfig, path.join(E2E, 'repos', row.repo)) && bytes(path.join(codexHome, 'cloud-skills.json')).equals(bytes(path.join(run, 'cloud-skills.input.json'))), { baseline_final_config: oldFinalConfigPath, baseline_final_sha256: sha(oldFinalConfig), new_final_sha256: sha(finalConfig), allowed_runtime_append: 'Exact canonical template-project trusted section, byte-identical to the corresponding E2E2 session.' });
      const policies = compareParsedPolicies(oldFinalConfig, finalConfig);
      check(`${prefix}parsed_config_policies_unchanged`, policies.policies_equal === true && policies.new.skillfetch_approval === 'approve' && policies.old.approval_policy === 'never' && policies.new.approval_policy === 'never' && policies.old.sandbox_mode === 'workspace-write' && policies.new.sandbox_mode === 'workspace-write' && policies.old.network_access === false && policies.new.network_access === false, { parsed_policies: policies });
      check(`${prefix}runtime_mcp_approve`, approval.command === '/opt/homebrew/bin/codex' && equal(approval.args, ['mcp', 'get', 'skillfetch']) && approval.exit_code === 0 && approval.default_tools_approval_mode === 'approve' && /^\s*default_tools_approval_mode:\s*approve\s*$/m.test(approvalText) && equal(task.mcp_approval_config, approval));
      const statusMessages = facts.received('mcpServerStatus/updated');
      const catalogOk = servers.length === 1 && servers[0].name === 'skillfetch' && servers[0].runtimeStatus === 'connected' && !servers[0].toolsError && TOOLS.every(tool => Object.hasOwn(servers[0].tools || {}, tool));
      const statusReplies = events.filter(event => event.direction === 'receive' && facts.sent('mcpServerStatus/list').some(request => request.message.id === event.message?.id));
      check(`${prefix}only_skillfetch_mcp`, catalogOk && statusReplies.length > 0 && statusReplies.every(event => Array.isArray(event.message?.result?.data) && event.message.result.data.length === 1 && event.message.result.data.every(server => server.name === 'skillfetch')) && statusMessages.every(event => !event.message.params?.server || event.message.params.server === 'skillfetch') && facts.mcp.every(event => event.message.params.item.server === 'skillfetch'));
      check(`${prefix}no_interactive_approval`, facts.interactive.length === 0 && facts.controllerToolCalls.length === 0 && facts.unexpectedControllerMethods.length === 0 && facts.mcp.every(event => !/approval policy is never/i.test(event.message.params.item.error?.message || '')), { interactive_request_count: facts.interactive.length, unexpected_controller_methods: [...new Set(facts.unexpectedControllerMethods.map(event => event.message.method))] });
      check(`${prefix}turn_lifecycle_complete`, task.status === 'COMPLETED' && facts.received('turn/started').length === 1 && facts.received('turn/completed').length === 1 && facts.received('turn/started')[0].message.params.turn.id === task.turn_id && facts.received('turn/completed')[0].message.params.turn.id === task.turn_id && turnStart.result?.turn?.id === task.turn_id && turnEnd.params?.turn?.id === task.turn_id && turnEnd.params.turn.status === 'completed' && equal(task.completion, turnEnd.params.turn) && !priorTurns.has(task.turn_id));
      const responsePairs = [['thread/start', start], ['turn/start', turnStart], ['account/read', account]];
      check(`${prefix}saved_responses_match_transcript`, responsePairs.every(([method, response]) => facts.sent(method).length === 1 && facts.sent(method)[0].message.id === response.id && events.some(event => event.direction === 'receive' && equal(event.message, response))) && facts.received('turn/completed').some(event => equal(event.message, turnEnd)));
      check(`${prefix}process_exit_recorded`, facts.exits.length === 1, { exit_event_count: facts.exits.length });
      check(`${prefix}cleanup_complete`, task.cleanup === 'DONE' && task.worktree === expectedWorktree && absent(task.worktree) && !worktrees[row.repo].includes(normalizedPath(task.worktree)) && absent(path.join(codexHome, 'auth.json')));
      taskEvidence.push({ id: row.id, repo: row.repo, worktree: task.worktree, home, thread_id: task.thread_id, turn_id: task.turn_id, execution_status: task.status, execution_started: task.execution_started, transcript_sha256: sha(bytes(path.join(directory, 'transcript.jsonl'))), observed_mcp_item_count: new Set(facts.mcp.map(event => event.message.params.item.id)).size, turn_start_count: facts.sent('turn/start').length, status: checks.slice(taskChecksBefore).every(check => check.status === 'PASS') ? 'PASS' : 'FAIL' });
    } catch (error) {
      check(`${prefix}evidence_readable`, false, { error_kind: error.code || error.name });
      taskEvidence.push(salvageTask(run, row));
    }
  }
  check('nineteen_distinct_fresh_threads_and_turns', threadIds.length === 19 && threadIds.every(id => typeof id === 'string' && id.length > 0) && turnIds.length === 19 && turnIds.every(id => typeof id === 'string' && id.length > 0) && new Set(threadIds).size === 19 && new Set(turnIds).size === 19);
  check('owned_root_removed_and_unregistered', absent(manifest.owned_worktree_root) && Object.values(worktrees).flat().every(value => value !== normalizedPath(manifest.owned_worktree_root) && !value.startsWith(`${normalizedPath(manifest.owned_worktree_root)}/`)));
  const reportHash = sha(bytes(path.join(E2E, 'codex-e2e.md')));
  check('old_report_preserved', reportHash === REPORT_SHA, { sha256: reportHash });
  check('e2e2_report_preserved', sha(bytes(path.join(E2E, 'codex-e2e-2.md'))) === SECOND_REPORT_SHA);
  check('finished_manifest_stable_during_audit', bytes(path.join(run, 'manifest.json')).equals(manifestBytes));
  return { schema_version: 1, status: checks.every(check => check.status === 'PASS') ? 'PASS' : 'FAIL', run_directory: run, manifest_status: manifest.status, manifest_sha256: sha(manifestBytes), owned_worktree_root: manifest.owned_worktree_root, checked: checks.length, passed: checks.filter(check => check.status === 'PASS').length, failed: checks.filter(check => check.status === 'FAIL').map(check => check.name), tasks: taskEvidence, checks };
}

function salvageTask(run, row) {
  const directory = path.join(run, 'tasks', row.id);
  let task = null;
  let events = null;
  try { task = read(path.join(directory, 'task.json')); } catch { /* Missing evidence stays explicit below. */ }
  try { events = lines(path.join(directory, 'transcript.jsonl')); } catch { /* A missing log does not prove zero submissions. */ }
  return {
    id: row.id, repo: row.repo, status: 'FAIL', execution_status: task?.status || 'MISSING_EVIDENCE',
    execution_started: task?.execution_started ?? null, thread_id: task?.thread_id ?? null,
    turn_id: task?.turn_id ?? null, worktree: task?.worktree ?? null,
    home: task ? path.join(directory, 'home') : null,
    transcript_present: events !== null,
    turn_start_count: events ? transcriptFacts(events).sent('turn/start').length : null,
  };
}

function cohortFacts(replicates, expectedRows) {
  const tasks = replicates.flatMap(replicate => replicate.tasks.map(task => ({ replicate: replicate.id, ...task })));
  const unique = field => tasks.length === 57 && tasks.every(task => typeof task[field] === 'string' && task[field].length > 0) && new Set(tasks.map(task => task[field])).size === 57;
  const exactThree = expectedRows.every(row => {
    const matching = tasks.filter(task => task.id === row.id);
    return matching.length === 3 && equal(matching.map(task => task.replicate).sort(), REPLICATES) && matching.every(task => task.turn_start_count === 1);
  });
  return {
    tasks, exact_three_submissions_per_id: tasks.length === 57 && exactThree,
    unique_threads: unique('thread_id'), unique_turns: unique('turn_id'),
    unique_worktrees: unique('worktree'), unique_homes: unique('home'),
    observed_turn_start_count: tasks.reduce((total, task) => total + (task.turn_start_count || 0), 0),
    missing_transcript_count: tasks.filter(task => task.turn_start_count === null).length,
    execution_status_counts: Object.fromEntries([...new Set(tasks.map(task => task.execution_status))].map(status => [status, tasks.filter(task => task.execution_status === status).length])),
  };
}

function verifyRoot(root, agentsSource = AGENTS_SOURCE) {
  const rootBytes = bytes(path.join(root, 'manifest.json'));
  const manifest = JSON.parse(rootBytes);
  if (!['COMPLETED', 'COMPLETED_WITH_FAILURES', 'FAILED', 'INTERRUPTED'].includes(manifest.status) || !manifest.finished_at) throw new Error('Refusing final audit before the wrapper has finished');
  const checks = [];
  const check = (name, passed, evidence = {}) => checks.push({ name, status: passed === true ? 'PASS' : 'FAIL', ...evidence });
  const expectedRows = lines(path.join(OLD, 'tasks.jsonl'));
  const agentsBytes = bytes(agentsSource);
  const oldManifest = read(path.join(OLD, 'manifest.json'));
  check('controlled_full_agents_source', path.resolve(agentsSource) === AGENTS_SOURCE && sha(agentsBytes) === AGENTS_SHA, { source_path: agentsSource, sha256: sha(agentsBytes), bytes: agentsBytes.length });
  check('wrapper_experiment_complete', manifest.experiment === 'codex-e2e-3' && manifest.status === 'COMPLETED');
  check('three_declared_replicates', Array.isArray(manifest.replicates) && equal(manifest.replicates.map(item => item.id), REPLICATES));
  const fixed = manifest.fixed || {};
  check('wrapper_fixed_identity', fixed.source_commit === SOURCE_COMMIT && equal(fixed.repository_refs, oldManifest.repository_refs) && fixed.codex_version === 'codex-cli 0.164.0' && fixed.model === 'gpt-6-astra' && fixed.reasoning_effort === 'medium' && fixed.auth_type === 'chatgpt' && fixed.auth_plan_type === 'pro' && fixed.concurrency === 4 && fixed.replicates === 3 && fixed.tasks_per_replicate === 19, { fixed });
  const inputFiles = { tasks: 'tasks.jsonl', agents: null, config: 'config.input.toml', source_preflight: 'source-preflight.json', cloud_skills: 'cloud-skills.input.json' };
  for (const [key, baselineFile] of Object.entries(inputFiles)) {
    try {
      const input = manifest.inputs?.[key];
      const expected = baselineFile ? bytes(path.join(OLD, baselineFile)) : agentsBytes;
      const snapshot = path.resolve(root, input.snapshot_path);
      const captured = bytes(snapshot);
      check(`wrapper_input_${key}`, snapshot.startsWith(`${root}${path.sep}`) && captured.equals(expected) && captured.equals(bytes(input.original_path)) && input.sha256 === sha(captured) && input.bytes === captured.length, { snapshot_path: snapshot, sha256: sha(captured) });
    } catch (error) { check(`wrapper_input_${key}`, false, { error_kind: error.code || error.name }); }
  }
  try {
    check('task_runner_provenance', sha(bytes(manifest.task_runner.path)) === manifest.task_runner.sha256 && sha(bytes(manifest.task_runner.baseline_path)) === manifest.task_runner.baseline_sha256, { runner_path: manifest.task_runner.path, runner_sha256: manifest.task_runner.sha256 });
  } catch (error) { check('task_runner_provenance', false, { error_kind: error.code || error.name }); }
  const replicates = REPLICATES.map(id => {
    const run = path.join(root, id);
    const record = manifest.replicates?.find(item => item.id === id);
    let result;
    try { result = verifyReplicate(run, agentsBytes); }
    catch (error) {
      result = { status: 'FAIL', run_directory: run, checked: 1, passed: 0, failed: ['replicate_evidence_readable'], checks: [{ name: 'replicate_evidence_readable', status: 'FAIL', error_kind: error.code || error.name }], tasks: expectedRows.map(row => salvageTask(run, row)) };
    }
    const submitted = result.tasks.filter(task => task.turn_start_count === 1).length;
    const completed = result.tasks.filter(task => task.execution_status === 'COMPLETED').length;
    check(`${id}:wrapper_record_matches_evidence`, record?.run_dir === run && record.manifest_path === path.join(run, 'manifest.json') && record.manifest_sha256 === result.manifest_sha256 && record.status === result.manifest_status && record.exit_code === 0 && record.signal == null && record.submitted_count === submitted && record.completed_count === completed && record.not_run_count === 0 && record.cleanup_complete === true, { observed_single_submissions: submitted, observed_completed: completed });
    return { id, ...result };
  });
  const cohort = cohortFacts(replicates, expectedRows);
  check('wrapper_session_totals_match_raw_evidence', manifest.expected_sessions === 57 && manifest.submitted_sessions === cohort.observed_turn_start_count && manifest.completed_sessions === (cohort.execution_status_counts.COMPLETED || 0) && manifest.submitted_sessions === 57 && manifest.completed_sessions === 57, { expected_sessions: manifest.expected_sessions, submitted_sessions: manifest.submitted_sessions, completed_sessions: manifest.completed_sessions });
  check('57_slots_each_task_exactly_three_single_submissions', cohort.exact_three_submissions_per_id, { expected_slots: 57, observed_slots: cohort.tasks.length, observed_turn_start_count: cohort.observed_turn_start_count, missing_transcript_count: cohort.missing_transcript_count });
  for (const [field, value] of Object.entries({ threads: cohort.unique_threads, turns: cohort.unique_turns, worktrees: cohort.unique_worktrees, homes: cohort.unique_homes })) check(`57_distinct_${field}`, value);
  check('three_fresh_owned_worktree_roots', replicates.every(item => typeof item.owned_worktree_root === 'string' && item.owned_worktree_root !== oldManifest.owned_worktree_root) && new Set(replicates.map(item => item.owned_worktree_root)).size === 3);
  check('only_three_replicate_directories', equal(fs.readdirSync(root).filter(name => /^r\d+$/.test(name)).sort(), REPLICATES));
  check('old_reports_preserved', sha(bytes(path.join(E2E, 'codex-e2e.md'))) === REPORT_SHA && sha(bytes(path.join(E2E, 'codex-e2e-2.md'))) === SECOND_REPORT_SHA, { first_sha256: REPORT_SHA, second_sha256: SECOND_REPORT_SHA });
  check('wrapper_manifest_stable_during_audit', rootBytes.equals(bytes(path.join(root, 'manifest.json'))));
  const combined = [...checks, ...replicates.flatMap(replicate => replicate.checks.map(item => ({ ...item, name: `${replicate.id}:${item.name}` })))];
  return {
    schema_version: 1, experiment: 'codex-e2e-3', audited_at: new Date().toISOString(),
    status: combined.every(item => item.status === 'PASS') ? 'PASS' : 'FAIL',
    scope: 'Offline protocol, input identity, isolation, exact-once per replicate, and cleanup audit. Project output quality and skill-selection correctness are not evaluated. Missing transcripts retain unknown submission counts, not inferred zero.',
    run_root: root, manifest_sha256: sha(rootBytes), auditor_sha256: sha(bytes(__filename)),
    checked: combined.length, passed: combined.filter(item => item.status === 'PASS').length,
    failed: combined.filter(item => item.status === 'FAIL').map(item => item.name),
    totals: { expected_sessions: 57, recorded_slots: cohort.tasks.length, observed_turn_start_count: cohort.observed_turn_start_count, missing_transcript_count: cohort.missing_transcript_count, execution_status_counts: cohort.execution_status_counts, passing_sessions: cohort.tasks.filter(task => task.status === 'PASS').length },
    tasks: cohort.tasks, checks, replicates,
  };
}

function main(argv) {
  if (argv.length === 1 && ['--help', '-h'].includes(argv[0])) {
    process.stdout.write('Usage: node codex-e2e-3-verify.cjs --run-root DIR [--agents-file FILE] [--agents-sha256 HASH] [--out FILE]\nReads finished r1/r2/r3 evidence only. No model calls, network calls, repairs, credential reads, or output-quality grading.\n');
    return;
  }
  const options = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    if (!['--run-root', '--agents-file', '--agents-sha256', '--out'].includes(key) || options[key] || !argv[index + 1] || argv[index + 1].startsWith('--')) throw new Error('Invalid arguments');
    options[key] = key === '--agents-sha256' ? argv[index + 1] : path.resolve(argv[index + 1]);
  }
  if (!options['--run-root']) throw new Error('--run-root is required');
  if (options['--agents-sha256'] && options['--agents-sha256'] !== AGENTS_SHA) throw new Error('AGENTS hash differs from the preregistered full router');
  const run = fs.realpathSync(options['--run-root']);
  const output = options['--out'] || path.join(run, 'audit-verification.json');
  if (!absent(output)) throw new Error('Refusing to overwrite an existing audit');
  const result = verifyRoot(run, options['--agents-file'] || AGENTS_SOURCE);
  fs.writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`, { flag: 'wx', mode: 0o600 });
  process.stdout.write(`${result.status}: ${result.passed}/${result.checked} checks; ${output}\n`);
  if (result.status !== 'PASS') process.exitCode = 1;
}

module.exports = { finalConfigMatches, compareParsedPolicies, transcriptFacts, appliedAgentsValid, salvageTask, cohortFacts, verifyReplicate, verifyRoot };
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
}
