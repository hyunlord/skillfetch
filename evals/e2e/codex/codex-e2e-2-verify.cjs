#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const { isDeepStrictEqual: equal } = require('node:util');

const E2E = __dirname;
const OLD = path.join(E2E, 'codex-e2e-runs/20261023-subscription-14d2020');
const SOURCE_COMMIT = '14d2020f1275e10a272eb46575c9bd6d4a2182e4';
const REPORT_SHA = 'db5b22600f4d20048f5669a39221335d8b5f7106cd1824d4b2deb57848d139c5';
const OLD_CONFIG_SHA = 'a730b036b1467e899c3402226121f3ef02c7fcbc6403851efb88c3f64a6af869';
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

function configOnlyApproval(oldConfig, newConfig) {
  const section = '[mcp_servers.skillfetch]\n';
  return oldConfig.split(section).length === 2 &&
    newConfig === oldConfig.replace(section, `${section}default_tools_approval_mode = "approve"\n`);
}

function finalConfigMatches(oldInput, newInput, oldFinal, newFinal, repoPath) {
  const trust = `\n[projects.${JSON.stringify(repoPath)}]\ntrust_level = "trusted"\n`;
  return oldFinal === oldInput + trust && newFinal === newInput + trust && configOnlyApproval(oldFinal, newFinal);
}

function compareParsedPolicies(oldConfig, newConfig) {
  const program = [
    'import json, sys, tomllib',
    'old_text, new_text = json.load(sys.stdin)',
    'old, new = tomllib.loads(old_text), tomllib.loads(new_text)',
    'def policy(config):',
    '    return {"approval_policy": config.get("approval_policy"), "sandbox_mode": config.get("sandbox_mode"), "network_access": config.get("sandbox_workspace_write", {}).get("network_access"), "model": config.get("model"), "reasoning_effort": config.get("model_reasoning_effort"), "forced_login_method": config.get("forced_login_method"), "mcp_servers": sorted(config.get("mcp_servers", {})), "skillfetch_approval": config.get("mcp_servers", {}).get("skillfetch", {}).get("default_tools_approval_mode"), "projects": config.get("projects", {})}',
    'old_policy, new_policy = policy(old), policy(new)',
    'removed = new["mcp_servers"]["skillfetch"].pop("default_tools_approval_mode", None)',
    'print(json.dumps({"old": old_policy, "new": new_policy, "only_approval_difference": old == new and removed == "approve" and old_policy["skillfetch_approval"] is None}))',
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

function command(program, args) {
  const result = cp.spawnSync(program, args, { encoding: 'utf8', timeout: 30000, maxBuffer: 1024 * 1024 });
  if (result.error || result.status !== 0) throw new Error('Read-only verification command failed');
  return result.stdout.trim();
}

function verify(run) {
  const manifestBytes = bytes(path.join(run, 'manifest.json'));
  const manifest = JSON.parse(manifestBytes);
  if (!['COMPLETED', 'COMPLETED_WITH_FAILURES'].includes(manifest.status) || !manifest.finished_at) {
    throw new Error('Refusing final audit before the runner manifest is finished');
  }
  const checks = [];
  const check = (name, passed, evidence = {}) => checks.push({ name, status: passed === true ? 'PASS' : 'FAIL', ...evidence });
  const old = read(path.join(OLD, 'manifest.json'));
  const priorManifests = [old, read(path.join(`${OLD}-unsubmitted`, 'manifest.json'))];
  const priorThreads = new Set(priorManifests.flatMap(m => m.tasks.map(task => task.thread_id).filter(Boolean)));
  const priorTurns = new Set(priorManifests.flatMap(m => m.tasks.map(task => task.turn_id).filter(Boolean)));
  const rows = lines(path.join(run, 'tasks.jsonl'));
  const oldRows = lines(path.join(OLD, 'tasks.jsonl'));
  const preflight = read(path.join(run, 'source-preflight.json'));
  const config = bytes(path.join(run, 'config.input.toml'));
  const oldConfig = bytes(path.join(OLD, 'config.input.toml'));
  check('nineteen_unique_exact_inputs', rows.length === 19 && new Set(rows.map(row => row.id)).size === 19 && new Set(rows.map(row => row.prompt)).size === 19 && equal(rows, oldRows), { count: rows.length });
  check('manifest_task_identities', manifest.tasks.length === 19 && equal(manifest.tasks.map(task => ({ id: task.id, repo: task.repo, prompt_sha256: task.prompt_sha256 })), rows.map(row => ({ id: row.id, repo: row.repo, prompt_sha256: sha(row.prompt) }))));
  for (const [file, key] of [['tasks.jsonl', 'tasks_sha256'], ['AGENTS.input.md', 'agents_sha256'], ['cloud-skills.input.json', 'cloud_skills_sha256']]) {
    const current = bytes(path.join(run, file));
    check(`unchanged_${file}`, current.equals(bytes(path.join(OLD, file))) && sha(current) === manifest[key] && manifest[key] === old[key], { sha256: sha(current) });
  }
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
  check('only_skillfetch_approval_config_changed', sha(oldConfig) === OLD_CONFIG_SHA && configOnlyApproval(oldConfig.toString('utf8'), config.toString('utf8')) && sha(config) === manifest.config_sha256, { old_sha256: sha(oldConfig), new_sha256: sha(config) });
  check('cloud_skills_empty', equal(read(path.join(run, 'cloud-skills.input.json')).skills, []));
  check('run_controls_unchanged', manifest.concurrency === old.concurrency && manifest.timeout_seconds === old.timeout_seconds && manifest.assistant_round_cap === null && manifest.experimental_raw_events_requested === true && manifest.recovery_of === null && !manifest.runner_errors?.length, { concurrency: manifest.concurrency, timeout_seconds: manifest.timeout_seconds });
  check('requested_identity', manifest.requested_model === 'gpt-6-astra' && equal(manifest.repository_refs, old.repository_refs) && manifest.mcp_approval_config?.baseline_path === path.join(OLD, 'config.input.toml') && manifest.mcp_approval_config.baseline_sha256 === OLD_CONFIG_SHA && manifest.mcp_approval_config.default_tools_approval_mode === 'approve');
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
      const oldExecutedRoot = old.tasks.find(task => task.id === row.id)?.execution_started ? OLD : `${OLD}-unsubmitted`;
      const oldFinalConfigPath = path.join(oldExecutedRoot, 'tasks', row.id, 'home/.codex/config.toml');
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
      check(`${prefix}thread_policy_effective`, start.result?.approvalPolicy === 'never' && start.result.sandbox?.type === 'workspaceWrite' && start.result.sandbox.networkAccess === false && equal(start.result.sandbox.writableRoots, []));
      check(`${prefix}actual_model_auth`, task.model === 'gpt-6-astra' && task.reasoning_effort === 'medium' && task.model_provider === 'openai' && task.cli_version === '0.164.0' && start.result.model === task.model && start.result.reasoningEffort === task.reasoning_effort && start.result.modelProvider === task.model_provider && start.result.thread.cliVersion === task.cli_version && task.auth_mode === 'chatgpt' && task.auth_plan_type === 'pro' && account.result?.account?.type === 'chatgpt' && account.result.account.planType === 'pro');
      check(`${prefix}login_subscription_no_api_environment`, login.exit_code === 0 && login.chatgpt === true && login.output === 'Logged in using ChatGPT' && API_KEYS.every(key => login.api_key_environment_absent?.[key] === true) && equal(task.login_status, login));
      check(`${prefix}isolated_launch`, launch.command === '/opt/homebrew/bin/codex' && equal(launch.args, ['app-server', '--stdio', '--strict-config', '--cloud-skills-snapshot', path.join(codexHome, 'cloud-skills.json')]) && launch.cwd === expectedWorktree && launch.cwd === task.worktree && launch.env?.HOME === home && launch.env.CODEX_HOME === codexHome && launch.env.TMPDIR === path.join(directory, 'tmp') && typeof launch.env.PATH === 'string' && Object.keys(launch.env).every(key => ENV_KEYS.has(key)) && API_KEYS.every(key => !Object.hasOwn(launch.env, key)), { env_keys: Object.keys(launch.env || {}).sort() });
      check(`${prefix}config_only_approval_change_with_baseline_trust`, finalConfigMatches(oldConfig.toString('utf8'), config.toString('utf8'), oldFinalConfig, finalConfig, path.join(E2E, 'repos', row.repo)) && bytes(path.join(codexHome, 'cloud-skills.json')).equals(bytes(path.join(run, 'cloud-skills.input.json'))), { baseline_final_config: oldFinalConfigPath, baseline_final_sha256: sha(oldFinalConfig), new_final_sha256: sha(finalConfig), allowed_runtime_append: 'Exact canonical template-project trusted section, byte-identical to the corresponding old executed session.' });
      const policies = compareParsedPolicies(oldFinalConfig, finalConfig);
      check(`${prefix}parsed_config_policy_delta`, policies.only_approval_difference === true && policies.old.approval_policy === 'never' && policies.new.approval_policy === 'never' && policies.old.sandbox_mode === 'workspace-write' && policies.new.sandbox_mode === 'workspace-write' && policies.old.network_access === false && policies.new.network_access === false, { parsed_policies: policies });
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
      taskEvidence.push({ id: row.id, repo: row.repo, thread_id: task.thread_id, turn_id: task.turn_id, transcript_sha256: sha(bytes(path.join(directory, 'transcript.jsonl'))), observed_mcp_item_count: new Set(facts.mcp.map(event => event.message.params.item.id)).size, turn_start_count: facts.sent('turn/start').length, status: checks.slice(taskChecksBefore).every(check => check.status === 'PASS') ? 'PASS' : 'FAIL' });
    } catch (error) {
      check(`${prefix}evidence_readable`, false, { error_kind: error.code || error.name });
      taskEvidence.push({ id: row.id, status: 'FAIL' });
    }
  }
  check('nineteen_distinct_fresh_threads_and_turns', threadIds.length === 19 && threadIds.every(id => typeof id === 'string' && id.length > 0) && turnIds.length === 19 && turnIds.every(id => typeof id === 'string' && id.length > 0) && new Set(threadIds).size === 19 && new Set(turnIds).size === 19);
  check('owned_root_removed_and_unregistered', absent(manifest.owned_worktree_root) && Object.values(worktrees).flat().every(value => value !== normalizedPath(manifest.owned_worktree_root) && !value.startsWith(`${normalizedPath(manifest.owned_worktree_root)}/`)));
  const reportHash = sha(bytes(path.join(E2E, 'codex-e2e.md')));
  check('old_report_preserved', reportHash === REPORT_SHA, { sha256: reportHash });
  check('finished_manifest_stable_during_audit', bytes(path.join(run, 'manifest.json')).equals(manifestBytes));
  const initialAudit = path.join(run, 'audit-verification-initial.json');
  const correction = absent(initialAudit) ? null : {
    initial_audit_path: initialAudit,
    initial_audit_sha256: sha(bytes(initialAudit)),
    initial_status: read(initialAudit).status,
    reason: 'The initial auditor compared final task-home config bytes directly with the input template. All corresponding old and new executed sessions append the same canonical template-project trusted section. The corrected check requires that exact baseline append, preserves the full input prefix, and permits only the skillfetch approval insertion between old and new final configs. Parsed TOML policies are also compared. No model sessions were rerun and no session evidence was modified.',
  };
  return { schema_version: 1, audited_at: new Date().toISOString(), status: checks.every(check => check.status === 'PASS') ? 'PASS' : 'FAIL', scope: 'Run identity, isolation, exact-once submission and cleanup only; project output correctness is not evaluated.', run_directory: run, baseline_run_directory: OLD, manifest_sha256: sha(manifestBytes), auditor_sha256: sha(bytes(__filename)), auditor_correction: correction, checked: checks.length, passed: checks.filter(check => check.status === 'PASS').length, failed: checks.filter(check => check.status === 'FAIL').map(check => check.name), tasks: taskEvidence, checks };
}

function main(argv) {
  if (argv.length === 1 && ['--help', '-h'].includes(argv[0])) {
    process.stdout.write('Usage: node codex-e2e-2-verify.cjs --run-dir DIR [--out FILE]\nReads completed local evidence only. No model calls, network calls, repairs, or credential reads.\n');
    return;
  }
  const options = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    if (!['--run-dir', '--out'].includes(key) || options[key] || !argv[index + 1] || argv[index + 1].startsWith('--')) throw new Error('Invalid arguments');
    options[key] = path.resolve(argv[index + 1]);
  }
  if (!options['--run-dir']) throw new Error('--run-dir is required');
  const run = fs.realpathSync(options['--run-dir']);
  const output = options['--out'] || path.join(run, 'audit-verification.json');
  if (!absent(output)) throw new Error('Refusing to overwrite an existing audit');
  const result = verify(run);
  fs.writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`, { flag: 'wx', mode: 0o600 });
  process.stdout.write(`${result.status}: ${result.passed}/${result.checked} checks; ${output}\n`);
  if (result.status !== 'PASS') process.exitCode = 1;
}

module.exports = { configOnlyApproval, finalConfigMatches, compareParsedPolicies, transcriptFacts, verify };
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
}
