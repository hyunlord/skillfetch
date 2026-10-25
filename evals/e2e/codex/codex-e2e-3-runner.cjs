#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const cp = require('node:child_process');
const crypto = require('node:crypto');
const E2E = __dirname;
const TASK_RUNNER = path.join(E2E, 'codex-e2e-3-task-runner.cjs');
const BASELINE_RUNNER = path.join(E2E, 'codex-e2e-2-runner.cjs');
const TASKS = path.join(E2E, 'stage5/tasks.jsonl');
const helpers = require(TASK_RUNNER);
const FIXED = {
  source_commit: '14d2020f1275e10a272eb46575c9bd6d4a2182e4',
  repository_refs: { fastapi: '2b38acb4586092ef0318bc6a8ab36436ba8fc09a', nextjs: '2a1df71575f0c45a0f7a999bf77f4286d81e8706' },
  codex_version: 'codex-cli 0.164.0', model: 'gpt-6-astra', reasoning_effort: 'medium',
  auth_type: 'chatgpt', auth_plan_type: 'pro', concurrency: 4, replicates: 3, tasks_per_replicate: 19,
  approval_policy: 'never', sandbox_mode: 'workspace-write', shell_network_access: false,
  mcp_server: 'skillfetch', mcp_default_tools_approval_mode: 'approve', timeout_seconds: 2700,
};
const INPUTS = {
  agents: ['agents-file', 'AGENTS.md'], config: ['config-template', 'config.toml'],
  source_preflight: ['source-preflight', 'source-preflight.json'], cloud_skills: ['cloud-skills-snapshot', 'cloud-skills.json'],
};
const HELP = `Usage: node codex-e2e-3-runner.cjs --run-root NEW_DIRECTORY
  --config-template FILE --agents-file FILE --source-preflight FILE
  --cloud-skills-snapshot FILE --auth-file FILE --allow-codex-inference
  [--model gpt-6-astra]

Runs r1, r2, r3 sequentially, 19 exact prompts each, concurrency 4 total.
Existing roots and retries are refused. Every child preserves its raw logs.
Signals are forwarded to the active runner; the wrapper waits for its cleanup.
`;

function ensure(ok, message) { if (!ok) throw new Error(message); }
function sha256(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }
function writeJson(file, value) {
  const temporary = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temporary, file);
}

function parseArgs(argv) {
  if (argv.length === 1 && ['--help', '-h'].includes(argv[0])) return { help: true };
  const options = { model: FIXED.model };
  const valued = new Set(['run-root', 'config-template', 'agents-file', 'source-preflight', 'cloud-skills-snapshot', 'auth-file', 'model']);
  const seen = new Set();
  for (let i = 0; i < argv.length; i++) {
    const name = argv[i].replace(/^--/, '');
    ensure(argv[i].startsWith('--') && !seen.has(name), `Unknown or repeated argument: ${argv[i]}`);
    seen.add(name);
    if (name === 'allow-codex-inference') options[name] = true;
    else {
      ensure(valued.has(name) && argv[i + 1] && !argv[i + 1].startsWith('--'), `Invalid argument/value: ${argv[i]}`);
      options[name] = argv[++i];
    }
  }
  ensure(options['allow-codex-inference'] === true, 'NOT_RUN: --allow-codex-inference is required');
  for (const name of [...valued].filter(name => name !== 'model')) {
    ensure(typeof options[name] === 'string', `Missing --${name}`);
    options[name] = path.resolve(options[name]);
  }
  ensure(options.model === FIXED.model, 'Only the fixed gpt-6-astra model is allowed');
  return options;
}

function git(repo, args) {
  return cp.execFileSync('git', ['-C', path.join(E2E, 'repos', repo), ...args], { encoding: 'utf8', timeout: 30000 }).trim();
}

function verifyFixedRefs() {
  for (const [repo, expected] of Object.entries(FIXED.repository_refs)) {
    ensure(git(repo, ['rev-parse', '--verify', 'refs/heads/s5^{commit}']) === expected, `s5 differs from the fixed ${repo} baseline`);
  }
}

function buildChildArgs(options, runDirectory, inputs) {
  const args = [TASK_RUNNER, '--run-dir', runDirectory, '--allow-codex-inference', '--concurrency', '4', '--timeout-seconds', '2700', '--model', FIXED.model];
  for (const [name, [flag]] of Object.entries(INPUTS)) args.push(`--${flag}`, inputs[name].snapshot_path);
  args.push('--auth-file', options['auth-file']);
  return args;
}

function verifyInputs(manifest) {
  for (const [name, input] of Object.entries(manifest.inputs)) {
    ensure(sha256(fs.readFileSync(input.original_path)) === input.sha256, `Original input changed: ${name}`);
    ensure(sha256(fs.readFileSync(input.snapshot_path)) === input.sha256, `Frozen input changed: ${name}`);
  }
  ensure(sha256(fs.readFileSync(TASK_RUNNER)) === manifest.task_runner.sha256, 'Task runner changed during the experiment');
  ensure(sha256(fs.readFileSync(BASELINE_RUNNER)) === manifest.task_runner.baseline_sha256, 'Prior runner changed during the experiment');
  const source = JSON.parse(fs.readFileSync(manifest.inputs.source_preflight.snapshot_path));
  ensure(source.source_commit === FIXED.source_commit, 'Source commit differs from the fixed baseline');
  helpers.verifyPreflight(source);
  helpers.verifyApprovalConfig(fs.readFileSync(manifest.inputs.config.snapshot_path));
  verifyFixedRefs();
}

function validateChildManifest(child, parent, rows) {
  ensure(['COMPLETED', 'COMPLETED_WITH_FAILURES', 'INTERRUPTED'].includes(child.status) && child.finished_at,
    'Child runner did not leave a finished manifest');
  for (const [key, input] of Object.entries({ tasks_sha256: 'tasks', agents_sha256: 'agents', config_sha256: 'config', cloud_skills_sha256: 'cloud_skills' })) {
    ensure(child[key] === parent.inputs[input].sha256, `Child input identity differs: ${key}`);
  }
  ensure(child.source_commit === FIXED.source_commit && child.codex_version === FIXED.codex_version && child.concurrency === 4 && child.timeout_seconds === 2700,
    'Child execution settings differ from the fixed experiment');
  for (const [repo, sha] of Object.entries(FIXED.repository_refs)) ensure(child.repository_refs?.[repo] === sha, `Child pinned commit differs: ${repo}`);
  ensure(Array.isArray(child.tasks) && child.tasks.length === 19 && new Set(child.tasks.map(task => task.id)).size === 19, 'Child did not retain all 19 unique task slots');
  for (const row of rows) {
    const task = child.tasks.find(item => item.id === row.id);
    ensure(task && task.repo === row.repo && task.prompt_sha256 === sha256(row.prompt), `Child task identity differs: ${row.id}`);
    ensure(!task.turn_start_requested || ['COMPLETED', 'FAILED', 'INTERRUPTED', 'TIMEOUT', 'USER_INPUT_REQUIRED', 'FAILED_AFTER_START_REQUEST'].includes(task.status),
      `Child task remains active: ${row.id}`);
    if (task.turn_start_requested) ensure(task.model === FIXED.model && task.reasoning_effort === FIXED.reasoning_effort && task.cli_version === '0.164.0' &&
      task.auth_mode === FIXED.auth_type && task.auth_plan_type === FIXED.auth_plan_type, `Child runtime identity differs: ${row.id}`);
    ensure(!task.worktree || (!fs.existsSync(task.worktree) && task.cleanup === 'DONE'), `Child worktree was not cleaned: ${row.id}`);
  }
  ensure(!fs.existsSync(child.owned_worktree_root), 'Child owned-worktree root remains after exit');
  return {
    submitted_count: child.tasks.filter(task => task.turn_start_requested === true).length,
    completed_count: child.tasks.filter(task => task.status === 'COMPLETED').length,
    not_run_count: child.tasks.filter(task => task.turn_start_requested !== true).length,
    cleanup_complete: true,
  };
}

async function runReplicate(options, parent, replicate, control) {
  const args = buildChildArgs(options, replicate.run_dir, parent.inputs);
  const stdoutPath = path.join(options['run-root'], 'logs', `${replicate.id}.stdout.log`);
  const stderrPath = path.join(options['run-root'], 'logs', `${replicate.id}.stderr.log`);
  const stdout = fs.openSync(stdoutPath, 'wx', 0o600);
  let stderr;
  try {
    stderr = fs.openSync(stderrPath, 'wx', 0o600);
    Object.assign(replicate, { status: 'RUNNING', started_at: new Date().toISOString(), stdout_path: stdoutPath, stderr_path: stderrPath, command: process.execPath, args });
    control.save();
    const env = { PATH: process.env.PATH || '/opt/homebrew/bin:/usr/bin:/bin', HOME: process.env.HOME };
    for (const name of ['TMPDIR', 'LANG', 'LC_ALL', 'TERM']) if (process.env[name]) env[name] = process.env[name];
    const result = await new Promise(resolve => {
      const child = cp.spawn(process.execPath, args, { cwd: E2E, env, stdio: ['ignore', stdout, stderr] });
      control.child = child;
      replicate.pid = child.pid;
      let spawnError;
      child.on('error', error => { spawnError = error.message; });
      child.on('close', (code, signal) => {
        control.child = null;
        resolve({ exit_code: code, signal, ...(spawnError ? { spawn_error: spawnError } : {}) });
      });
      try { control.save(); } catch (error) { spawnError = error.message; child.kill('SIGTERM'); }
      if (control.signal) child.kill(control.signal);
    });
    Object.assign(replicate, result, { finished_at: new Date().toISOString() });
    ensure(!result.spawn_error, `Child launch failed: ${result.spawn_error}`);
    ensure(fs.existsSync(replicate.manifest_path), 'Child runner exited without a manifest');
    const bytes = fs.readFileSync(replicate.manifest_path);
    const childManifest = JSON.parse(bytes);
    replicate.manifest_sha256 = sha256(bytes);
    Object.assign(replicate, validateChildManifest(childManifest, parent, control.rows));
    replicate.status = childManifest.status;
    if (control.signal) replicate.status = 'INTERRUPTED';
    else ensure((result.exit_code === 0 && replicate.status === 'COMPLETED') ||
      (result.exit_code === 1 && replicate.status === 'COMPLETED_WITH_FAILURES'), 'Child exit code and terminal status disagree');
    control.save();
  } finally {
    fs.closeSync(stdout);
    if (stderr !== undefined) fs.closeSync(stderr);
  }
}

async function main(argv) {
  const options = parseArgs(argv);
  if (options.help) { process.stdout.write(HELP); return; }
  ensure(!fs.existsSync(options['run-root']), 'Existing run root is refused; this wrapper never resumes or retries');
  const taskBytes = fs.readFileSync(TASKS);
  const rows = helpers.readTasks(taskBytes);
  const bytes = Object.fromEntries(Object.entries(INPUTS).map(([name, [flag]]) => [name, fs.readFileSync(options[flag])]));
  ensure(bytes.agents.length > 0, 'AGENTS input is empty');
  helpers.verifyApprovalConfig(bytes.config);
  const preflight = JSON.parse(bytes.source_preflight);
  ensure(preflight.source_commit === FIXED.source_commit, 'Unexpected source commit');
  helpers.verifyPreflight(preflight);
  const cloud = JSON.parse(bytes.cloud_skills);
  ensure(Array.isArray(cloud.skills) && cloud.skills.length === 0, 'Only an empty frozen cloud-skills snapshot is allowed');
  ensure(fs.statSync(options['auth-file']).isFile(), 'Auth path is not a file');
  const version = cp.execFileSync('/opt/homebrew/bin/codex', ['--version'], { encoding: 'utf8', timeout: 30000 }).trim();
  ensure(version === FIXED.codex_version, 'CLI version differs from 0.164.0');
  verifyFixedRefs();
  fs.mkdirSync(path.dirname(options['run-root']), { recursive: true });
  fs.mkdirSync(options['run-root'], { mode: 0o700 });
  const inputDirectory = path.join(options['run-root'], 'inputs');
  fs.mkdirSync(inputDirectory, { mode: 0o700 });
  fs.mkdirSync(path.join(options['run-root'], 'logs'), { mode: 0o700 });
  const inputs = { tasks: { original_path: TASKS, snapshot_path: path.join(inputDirectory, 'tasks.jsonl'), sha256: sha256(taskBytes), bytes: taskBytes.length } };
  fs.writeFileSync(inputs.tasks.snapshot_path, taskBytes, { mode: 0o600 });
  for (const [name, [flag, filename]] of Object.entries(INPUTS)) {
    const snapshot = path.join(inputDirectory, filename);
    fs.writeFileSync(snapshot, bytes[name], { mode: 0o600 });
    inputs[name] = { original_path: options[flag], snapshot_path: snapshot, sha256: sha256(bytes[name]), bytes: bytes[name].length };
  }
  const manifest = {
    schema_version: 1, experiment: 'codex-e2e-3', status: 'RUNNING', created_at: new Date().toISOString(), pid: process.pid,
    fixed: FIXED, inputs, expected_sessions: 57, inference_explicitly_allowed: true,
    wrapper: { path: __filename, sha256: sha256(fs.readFileSync(__filename)) },
    task_runner: { path: TASK_RUNNER, sha256: sha256(fs.readFileSync(TASK_RUNNER)), baseline_path: BASELINE_RUNNER, baseline_sha256: sha256(fs.readFileSync(BASELINE_RUNNER)),
      changes_from_baseline: ['AGENTS byte/hash verification and evidence after copy and immediately before turn/start'] },
    replicates: ['r1', 'r2', 'r3'].map(id => ({ id, run_dir: path.join(options['run-root'], id), manifest_path: path.join(options['run-root'], id, 'manifest.json'), status: 'NOT_RUN', tasks_expected: 19 })),
  };
  const control = { child: null, signal: null, rows, save: () => writeJson(path.join(options['run-root'], 'manifest.json'), manifest) };
  control.save();
  const forwardSignal = signal => {
    if (!control.signal) {
      control.signal = signal;
      manifest.stop_requested = { signal, at: new Date().toISOString() };
      try { control.save(); } catch (error) { manifest.error = error.message; }
      if (control.child) control.child.kill(signal);
    }
  };
  const sigint = () => forwardSignal('SIGINT');
  const sigterm = () => forwardSignal('SIGTERM');
  process.on('SIGINT', sigint);
  process.on('SIGTERM', sigterm);
  try {
    for (const replicate of manifest.replicates) {
      if (control.signal) break;
      try {
        verifyInputs(manifest);
        process.stdout.write(`${replicate.id}: starting 19 tasks with concurrency 4\n`);
        await runReplicate(options, manifest, replicate, control);
        process.stdout.write(`${replicate.id}: ${replicate.status}; submitted=${replicate.submitted_count}; completed=${replicate.completed_count}\n`);
      } catch (error) {
        replicate.status = control.signal ? 'INTERRUPTED' : 'FAILED';
        replicate.error = error.message;
        replicate.finished_at = new Date().toISOString();
        manifest.error = error.message;
        break;
      } finally { control.save(); }
    }
  } finally {
    process.off('SIGINT', sigint);
    process.off('SIGTERM', sigterm);
    manifest.finished_at = new Date().toISOString();
    manifest.submitted_sessions = manifest.replicates.reduce((sum, replicate) => sum + (replicate.submitted_count || 0), 0);
    manifest.completed_sessions = manifest.replicates.reduce((sum, replicate) => sum + (replicate.completed_count || 0), 0);
    manifest.status = control.signal ? 'INTERRUPTED' : manifest.error ? 'FAILED' :
      manifest.replicates.every(replicate => replicate.status === 'COMPLETED') ? 'COMPLETED' : 'COMPLETED_WITH_FAILURES';
    control.save();
    if (manifest.status !== 'COMPLETED') process.exitCode = control.signal === 'SIGINT' ? 130 : control.signal === 'SIGTERM' ? 143 : 1;
  }
}

module.exports = { parseArgs, buildChildArgs, validateChildManifest, FIXED };
if (require.main === module) main(process.argv.slice(2)).catch(error => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
