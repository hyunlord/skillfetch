#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const readline = require('node:readline');

const CODEX = '/opt/homebrew/bin/codex';
const SOURCE_COMMIT = '14d2020f1275e10a272eb46575c9bd6d4a2182e4';
const E2E = __dirname;
const BASELINE_CONFIG = path.join(E2E, 'codex-e2e-runs/20261023-subscription-14d2020/config.input.toml');
const BASELINE_CONFIG_SHA256 = 'a730b036b1467e899c3402226121f3ef02c7fcbc6403851efb88c3f64a6af869';
const TASKS = path.join(E2E, 'stage5/tasks.jsonl');
const REPOS = Object.fromEntries(['fastapi', 'nextjs'].map(name => [name, path.join(E2E, 'repos', name)]));
const HELP = `Usage: node codex-e2e-2-runner.cjs --run-dir DIR --config-template FILE
  --agents-file FILE --source-preflight FILE --cloud-skills-snapshot FILE
  --allow-codex-inference
  [--auth-file FILE] [--model NAME] [--timeout-seconds 2700] [--concurrency 1]
  [--retry-unstarted-from COMPLETED_RUN_DIR]

Runs the 19 exact stage5/tasks.jsonl prompts, once each, with real Codex app-server.
Requires existing s5 branches in both template repositories. Never creates s5.
The inference flag is mandatory and must only be supplied after authorization.
The run directory must not exist; interrupted runs are never resumed or retried.
Source preflight must be PASS with source_commit, source_path, source_files,
index_path and index_files (relative path -> SHA256). Source/index hashes are
verified before each session. Credentials are symlinked without reading them.
No controller-side skillfetch tool calls or assistant-round caps are used.
Recovery selects only proven-unsubmitted NOT_RUN tasks from a completed original
run, uses its pinned commits, and atomically reserves each task against duplicates.
Requires CLI 0.164.0, gpt-6-astra/medium, ChatGPT Pro, and exactly one config
change from the prior run: skillfetch default_tools_approval_mode = "approve".
`;

function ensure(condition, message) {
  if (!condition) throw new Error(message);
}

function parseArgs(argv) {
  if (argv.length === 1 && ['--help', '-h'].includes(argv[0])) return { help: true };
  const result = { 'timeout-seconds': 2700, concurrency: 1 };
  const valued = new Set(['run-dir', 'config-template', 'agents-file', 'source-preflight', 'cloud-skills-snapshot', 'auth-file', 'model', 'timeout-seconds', 'concurrency', 'retry-unstarted-from']);
  const seen = new Set();
  for (let i = 0; i < argv.length; i++) {
    const name = argv[i].replace(/^--/, '');
    ensure(argv[i].startsWith('--') && !seen.has(name), `Unknown or repeated argument: ${argv[i]}`);
    seen.add(name);
    if (name === 'allow-codex-inference') result[name] = true;
    else {
      ensure(valued.has(name), `Unknown argument: ${argv[i]}`);
      ensure(argv[i + 1] && !argv[i + 1].startsWith('--'), `Missing value for --${name}`);
      result[name] = argv[++i];
    }
  }
  ensure(result['allow-codex-inference'] === true, 'NOT_RUN: explicit --allow-codex-inference is required');
  for (const name of ['run-dir', 'config-template', 'agents-file', 'source-preflight', 'cloud-skills-snapshot']) {
    ensure(typeof result[name] === 'string', `Missing --${name}`);
    result[name] = path.resolve(result[name]);
  }
  if (result['auth-file']) result['auth-file'] = path.resolve(result['auth-file']);
  if (result['retry-unstarted-from']) result['retry-unstarted-from'] = path.resolve(result['retry-unstarted-from']);
  for (const name of ['timeout-seconds', 'concurrency']) {
    result[name] = Number(result[name]);
    ensure(Number.isSafeInteger(result[name]) && result[name] > 0, `--${name} must be a positive integer`);
  }
  ensure(result.concurrency <= 19, '--concurrency cannot exceed the 19 measured tasks');
  ensure(result['timeout-seconds'] <= 2147483, '--timeout-seconds exceeds the Node timer limit');
  return result;
}

function sha256(bytes) {
  return crypto.createHash('sha256').update(bytes).digest('hex');
}

function json(file, value) {
  const temporary = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temporary, file);
}

function command(executable, args, options = {}) {
  const result = cp.spawnSync(executable, args, {
    encoding: 'utf8', timeout: 120000, maxBuffer: 32 * 1024 * 1024, ...options,
  });
  ensure(!result.error && result.status === 0,
    `${executable} ${args.join(' ')} failed: ${result.error?.message || result.stderr || result.status}`);
  return result.stdout.trim();
}

function readTasks(bytes) {
  const rows = bytes.toString('utf8').split(/\r?\n/).filter(line => line.trim()).map(line => JSON.parse(line));
  ensure(rows.length === 19, `Expected 19 tasks, received ${rows.length}`);
  ensure(new Set(rows.map(row => row.id)).size === 19, 'Task IDs must be unique');
  ensure(new Set(rows.map(row => row.prompt)).size === 19, 'Task prompts must be unique');
  for (const row of rows) {
    ensure(typeof row.id === 'string' && /^[A-Za-z0-9_-]+$/.test(row.id), 'Unsafe task ID');
    ensure(Object.hasOwn(REPOS, row.repo), `Unknown task repository: ${row.repo}`);
    ensure(typeof row.prompt === 'string' && row.prompt.trim().length > 0, `Missing prompt: ${row.id}`);
  }
  return rows;
}

function verifyFiles(root, hashes, label) {
  ensure(typeof root === 'string' && path.isAbsolute(root), `${label}_path must be absolute`);
  ensure(hashes && typeof hashes === 'object' && !Array.isArray(hashes) && Object.keys(hashes).length > 0,
    `${label}_files must contain SHA256 evidence`);
  const canonicalRoot = fs.realpathSync(root);
  for (const [relative, expected] of Object.entries(hashes)) {
    ensure(!path.isAbsolute(relative) && relative.split(/[\\/]/).every(part => part !== '..'), `Unsafe evidence path: ${relative}`);
    ensure(typeof expected === 'string' && /^[a-f0-9]{64}$/.test(expected), `Invalid SHA256: ${relative}`);
    const file = fs.realpathSync(path.join(canonicalRoot, relative));
    ensure(file.startsWith(`${canonicalRoot}${path.sep}`), `Evidence escapes ${label} root: ${relative}`);
    ensure(fs.statSync(file).isFile() && sha256(fs.readFileSync(file)) === expected, `Changed ${label} evidence: ${relative}`);
  }
}

function verifyPreflight(preflight) {
  ensure(preflight.status === 'PASS' && preflight.source_commit === SOURCE_COMMIT, 'Fixed source was not preflighted');
  verifyFiles(preflight.source_path, preflight.source_files, 'source');
  verifyFiles(preflight.index_path, preflight.index_files, 'index');
}

function validateMcp(servers) {
  ensure(servers.length === 1 && servers[0].name === 'skillfetch',
    `MCP isolation failed: expected only skillfetch, received ${servers.map(server => server.name).join(', ') || '(none)'}`);
  ensure(servers[0].runtimeStatus === 'connected' && !servers[0].toolsError, 'skillfetch is not connected with a valid tool catalog');
  for (const tool of ['profile_repo', 'search_skills', 'resolve_set', 'load_skills']) {
    ensure(Object.hasOwn(servers[0].tools || {}, tool), `skillfetch is missing required tool ${tool}`);
  }
}

async function awaitMcpConnected(rpc, threadId, directory, timeoutMs = 90000, pollMs = 1000) {
  const started = Date.now();
  const deadline = started + Math.min(timeoutMs, 90000);
  let poll = 0;
  while (Date.now() < deadline) {
    const servers = [];
    const cursors = new Set();
    let cursor;
    do {
      const remaining = deadline - Date.now();
      ensure(remaining > 0, 'skillfetch readiness timeout after 90 seconds');
      const status = await rpc.request('mcpServerStatus/list', { threadId, ...(cursor ? { cursor } : {}) }, Math.min(45000, remaining));
      ensure(Array.isArray(status.result?.data), 'Invalid MCP status response');
      servers.push(...status.result.data);
      // An additional server is a policy failure even if pagination is incomplete.
      ensure(servers.length <= 1 && servers.every(server => server.name === 'skillfetch'), 'MCP isolation failed during readiness polling');
      cursor = status.result.nextCursor;
      ensure(!cursor || !cursors.has(cursor), 'MCP status pagination repeated a cursor');
      if (cursor) cursors.add(cursor);
    } while (cursor);
    json(path.join(directory, 'mcp-status.json'), servers);
    fs.appendFileSync(path.join(directory, 'mcp-readiness-polls.jsonl'), `${JSON.stringify({
      poll: ++poll, at: new Date().toISOString(), elapsed_ms: Date.now() - started, servers,
    })}\n`);
    ensure(servers.length === 1 && servers[0].name === 'skillfetch', 'MCP isolation failed: expected exactly skillfetch');
    if (servers[0].runtimeStatus === 'connected') { validateMcp(servers); return servers; }
    ensure(servers[0].runtimeStatus === 'starting' && !servers[0].toolsError,
      `skillfetch readiness failed: ${servers[0].runtimeStatus}; ${servers[0].toolsError || 'no tool error'}`);
    if (rpc.fatal) throw rpc.fatal;
    const remaining = deadline - Date.now();
    if (remaining > 0) await new Promise(resolve => setTimeout(resolve, Math.min(pollMs, remaining)));
  }
  throw new Error('skillfetch readiness timeout after 90 seconds');
}

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}

function loadRecovery(options, rows, identity, preflight) {
  if (!options['retry-unstarted-from']) return null;
  const directory = fs.realpathSync(options['retry-unstarted-from']);
  const manifestBytes = fs.readFileSync(path.join(directory, 'manifest.json'));
  const prior = JSON.parse(manifestBytes);
  ensure(['COMPLETED', 'COMPLETED_WITH_FAILURES'].includes(prior.status) && typeof prior.finished_at === 'string',
    'Recovery requires a finished original manifest; RUNNING or interrupted runs are refused');
  ensure(!prior.recovery_of, 'Recovery from a recovery run is refused; claimed tasks cannot be resubmitted');
  ensure(Array.isArray(prior.tasks) && prior.tasks.length === 19 && new Set(prior.tasks.map(task => task.id)).size === 19,
    'Recovery manifest must describe the 19 unique original tasks');
  ensure(!prior.tasks.some(task => ['RUNNING', 'TURN_START_REQUESTED'].includes(task.status)), 'Recovery source still contains active tasks');
  for (const [key, expected] of Object.entries(identity)) ensure(prior[key] === expected, `Recovery identity mismatch: ${key}`);
  for (const [file, key] of [
    ['tasks.jsonl', 'tasks_sha256'], ['AGENTS.input.md', 'agents_sha256'],
    ['config.input.toml', 'config_sha256'], ['cloud-skills.input.json', 'cloud_skills_sha256'],
  ]) ensure(sha256(fs.readFileSync(path.join(directory, file))) === identity[key], `Recovery artifact mismatch: ${file}`);
  const priorPreflight = JSON.parse(fs.readFileSync(path.join(directory, 'source-preflight.json'), 'utf8'));
  ensure(canonical(priorPreflight) === canonical(preflight), 'Recovery source/index preflight identity mismatch');
  const models = prior.tasks.filter(task => task.model).map(task => ({
    model: task.model, model_provider: task.model_provider, reasoning_effort: task.reasoning_effort ?? null,
  }));
  ensure(models.length > 0 && models.every(model => canonical(model) === canonical(models[0])), 'Recovery cannot establish one original model configuration');
  ensure(models[0].model_provider === 'openai', 'Recovery source did not use the subscription model provider');
  ensure(!options.model || options.model === models[0].model, 'Recovery model override differs from the original model');
  for (const name of Object.keys(REPOS)) ensure(/^[a-f0-9]{40}$/.test(prior.repository_refs?.[name] || ''), `Invalid original pinned commit: ${name}`);
  const selected = [];
  const evidence = [];
  for (const row of rows) {
    const task = prior.tasks.find(item => item.id === row.id);
    ensure(task && task.repo === row.repo && task.prompt_sha256 === sha256(row.prompt), `Recovery task identity mismatch: ${row.id}`);
    if (task.status !== 'NOT_RUN' || task.turn_start_requested !== false || task.execution_started !== false) continue;
    ensure(!task.turn_id && !task.started_at && !task.turn_start_requested_at && !task.completion && task.cleanup === 'DONE', `Ambiguous prior task state: ${row.id}`);
    const taskDirectory = path.join(directory, 'tasks', row.id);
    const taskBytes = fs.readFileSync(path.join(taskDirectory, 'task.json'));
    ensure(canonical(JSON.parse(taskBytes)) === canonical(task), `Prior task/manifest evidence differs: ${row.id}`);
    const transcript = fs.readFileSync(path.join(taskDirectory, 'transcript.jsonl'));
    const events = transcript.toString('utf8').trim().split('\n').filter(Boolean).map(line => JSON.parse(line));
    ensure(events.length > 0 && events.every((event, index) => event.sequence === index + 1), `Missing or unordered original transcript: ${row.id}`);
    ensure(events.some(event => event.direction === 'process-exit'), `Prior app-server exit is unproven: ${row.id}`);
    ensure(!events.some(event => event.direction === 'send' && ['turn/start', 'turn/steer'].includes(event.message?.method)),
      `Task was already submitted: ${row.id}`);
    ensure(!events.some(event => event.direction === 'receive' && ['turn/started', 'turn/completed'].includes(event.message?.method)),
      `Task has prior execution evidence: ${row.id}`);
    const claim = path.join(directory, 'unstarted-claims', `${row.id}.json`);
    ensure(!fs.existsSync(claim), `Task already reserved by another recovery run: ${row.id}`);
    selected.push(row);
    evidence.push({ id: row.id, task_sha256: sha256(taskBytes), transcript_sha256: sha256(transcript), turn_start_sends: 0, claim });
  }
  ensure(selected.length > 0, 'No proven-unsubmitted NOT_RUN tasks remain');
  return { directory, manifest_sha256: sha256(manifestBytes), repository_refs: prior.repository_refs, expected_model: models[0], rows: selected, evidence };
}

function reserveRecovery(recovery, runDirectory) {
  if (!recovery) return;
  ensure(sha256(fs.readFileSync(path.join(recovery.directory, 'manifest.json'))) === recovery.manifest_sha256, 'Original manifest changed during recovery preparation');
  fs.mkdirSync(path.join(recovery.directory, 'unstarted-claims'), { recursive: true, mode: 0o700 });
  for (const task of recovery.evidence) {
    const directory = path.join(recovery.directory, 'tasks', task.id);
    ensure(sha256(fs.readFileSync(path.join(directory, 'task.json'))) === task.task_sha256 &&
      sha256(fs.readFileSync(path.join(directory, 'transcript.jsonl'))) === task.transcript_sha256, `Original task evidence changed: ${task.id}`);
    // Permanent exclusive reservation: a second destination cannot reuse stale NOT_RUN evidence.
    fs.writeFileSync(task.claim, `${JSON.stringify({
      claimed_at: new Date().toISOString(), run_directory: runDirectory,
      source_manifest_sha256: recovery.manifest_sha256, ...task,
    }, null, 2)}\n`, { flag: 'wx', mode: 0o600 });
  }
}

function isolatedEnvironment(home, codexHome, temporary) {
  const env = { PATH: process.env.PATH || '/opt/homebrew/bin:/usr/bin:/bin', HOME: home, CODEX_HOME: codexHome, TMPDIR: temporary };
  for (const key of ['LANG', 'LC_ALL', 'TERM']) if (process.env[key]) env[key] = process.env[key];
  return env;
}

function verifyLogin(directory, cwd, env) {
  const result = cp.spawnSync(CODEX, ['login', 'status'], { cwd, env, encoding: 'utf8', timeout: 30000 });
  const output = `${result.stdout || ''}${result.stderr || ''}`.trim();
  const chatgpt = result.status === 0 && /^Logged in using ChatGPT\s*$/i.test(output);
  const evidence = {
    checked_at: new Date().toISOString(), exit_code: result.status, chatgpt,
    output: chatgpt ? output : '[Unexpected auth output withheld to avoid exposing API-key material]',
    api_key_environment_absent: Object.fromEntries([
      'OPENAI_API_KEY', 'CODEX_API_KEY', 'AZURE_OPENAI_API_KEY', 'ANTHROPIC_API_KEY',
      'GOOGLE_API_KEY', 'GEMINI_API_KEY', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
    ].map(key => [key, !Object.hasOwn(env, key)])),
  };
  json(path.join(directory, 'login-status.json'), evidence);
  ensure(chatgpt, 'NOT_RUN: isolated codex login status did not confirm ChatGPT subscription authentication');
  return evidence;
}

function verifyApprovalConfig(configBytes) {
  const baseline = fs.readFileSync(BASELINE_CONFIG);
  ensure(sha256(baseline) === BASELINE_CONFIG_SHA256, 'Prior frozen config differs from the verified baseline');
  const lines = configBytes.toString('utf8').match(/[^\n]*\n|[^\n]+$/g) || [];
  let section = '';
  let approvalLines = 0;
  const retained = [];
  for (const line of lines) {
    const header = line.trim().match(/^\[([^\]]+)\]$/);
    if (header) section = header[1];
    if (/^\s*default_tools_approval_mode\s*=/.test(line)) {
      ensure(section === 'mcp_servers.skillfetch' && /^\s*default_tools_approval_mode\s*=\s*"approve"\s*$/.test(line),
        'MCP approval mode must be approve in the skillfetch server section');
      approvalLines++;
    } else retained.push(line);
  }
  ensure(approvalLines === 1 && Buffer.from(retained.join('')).equals(baseline),
    'Config must differ from the prior run by exactly the one skillfetch approval-mode line');
  return { baseline_path: BASELINE_CONFIG, baseline_sha256: BASELINE_CONFIG_SHA256, default_tools_approval_mode: 'approve' };
}

function verifyMcpApproval(directory, cwd, env) {
  const args = ['mcp', 'get', 'skillfetch'];
  const result = cp.spawnSync(CODEX, args, { cwd, env, encoding: 'utf8', timeout: 30000 });
  fs.writeFileSync(path.join(directory, 'mcp-get-skillfetch.stdout.txt'), result.stdout || '', { mode: 0o600 });
  fs.writeFileSync(path.join(directory, 'mcp-get-skillfetch.stderr.txt'), result.stderr || '', { mode: 0o600 });
  const approved = !result.error && result.status === 0 && /^\s*default_tools_approval_mode:\s*approve\s*$/m.test(result.stdout || '');
  const evidence = { checked_at: new Date().toISOString(), command: CODEX, args, exit_code: result.status, default_tools_approval_mode: approved ? 'approve' : null };
  json(path.join(directory, 'mcp-get-skillfetch.json'), evidence);
  ensure(approved, 'NOT_RUN: plain codex mcp get skillfetch did not confirm default_tools_approval_mode: approve');
  return evidence;
}

function verifyRuntimeIdentity(threadResult, account) {
  ensure(account?.type === 'chatgpt' && account.planType === 'pro', 'NOT_RUN: ChatGPT Pro subscription authentication is required');
  ensure(threadResult?.thread?.cliVersion === '0.164.0', 'NOT_RUN: actual thread CLI version must be 0.164.0');
  ensure((threadResult.model || threadResult.thread.model) === 'gpt-6-astra' && threadResult.reasoningEffort === 'medium',
    'NOT_RUN: actual thread model must be gpt-6-astra with medium reasoning');
}

class AppServer {
  constructor(directory, cwd, env, cloudSnapshot, observe) {
    this.sequence = 0;
    this.nextId = 0;
    this.pending = new Map();
    this.fatal = null;
    this.exited = false;
    this.directory = directory;
    this.observe = observe;
    const args = ['app-server', '--stdio', '--strict-config', '--cloud-skills-snapshot', cloudSnapshot];
    json(path.join(directory, 'launch.json'), { command: CODEX, args, cwd, env });
    this.child = cp.spawn(CODEX, args, { cwd, env, detached: true, stdio: ['pipe', 'pipe', 'pipe'] });
    this.child.stdin.on('error', error => this.fail(error));
    this.child.on('error', error => this.fail(error));
    this.closed = new Promise(resolve => this.child.on('close', (code, signal) => {
      this.exited = true;
      this.record('process-exit', { code, signal });
      this.fail(new Error(`app-server closed: code=${code} signal=${signal}`));
      resolve();
    }));
    this.child.stderr.on('data', chunk => {
      fs.appendFileSync(path.join(directory, 'stderr.log'), chunk);
      this.record('stderr', { base64: chunk.toString('base64'), text: chunk.toString('utf8') });
    });
    readline.createInterface({ input: this.child.stdout, crlfDelay: Infinity }).on('line', line => {
      let message;
      try { message = JSON.parse(line); } catch {
        this.record('invalid-stdout', { raw: line });
        this.fail(new Error('app-server emitted invalid JSON on stdout'));
        return;
      }
      const event = this.record('receive', { raw: line, message });
      try { this.observe(message, event); } catch (error) { this.fail(error); }
      if (message.id !== undefined && message.method) {
        this.send({ jsonrpc: '2.0', id: message.id, error: { code: -32601, message: 'No controller tool execution, approvals, or user input during a measured session' } });
        const error = new Error(`Unexpected interactive server request: ${message.method}`);
        error.code = 'USER_INPUT_REQUIRED';
        this.fail(error);
      } else if (message.id !== undefined && this.pending.has(message.id)) {
        const pending = this.pending.get(message.id);
        this.pending.delete(message.id);
        clearTimeout(pending.timer);
        if (message.error) pending.reject(new Error(`${pending.method}: ${JSON.stringify(message.error)}`));
        else pending.resolve(message);
      }
    });
  }

  record(direction, payload) {
    const event = { sequence: ++this.sequence, at: new Date().toISOString(), monotonic_ns: process.hrtime.bigint().toString(), direction, ...payload };
    fs.appendFileSync(path.join(this.directory, 'transcript.jsonl'), `${JSON.stringify(event)}\n`, { mode: 0o600 });
    return event;
  }

  send(message) {
    this.record('send', { message });
    this.child.stdin.write(`${JSON.stringify(message)}\n`);
  }

  request(method, params, timeout = 45000, allowAfterFailure = false) {
    if (this.fatal && !allowAfterFailure) return Promise.reject(this.fatal);
    return new Promise((resolve, reject) => {
      const id = ++this.nextId;
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Request timeout: ${method}`));
      }, timeout);
      this.pending.set(id, { resolve, reject, timer, method });
      try { this.send({ jsonrpc: '2.0', id, method, params }); }
      catch (error) { clearTimeout(timer); this.pending.delete(id); reject(error); }
    });
  }

  fail(error) {
    if (!this.fatal) {
      this.fatal = error;
      this.observe({ method: 'runner/failure', params: { message: error.message, code: error.code || 'ERROR' } });
    }
    for (const pending of this.pending.values()) { clearTimeout(pending.timer); pending.reject(error); }
    this.pending.clear();
  }

  async close() {
    if (!this.exited) {
      this.child.stdin.end();
      this.killGroup('SIGTERM');
      await Promise.race([this.closed, new Promise(resolve => setTimeout(resolve, 2000))]);
    }
    this.killGroup('SIGKILL');
    if (!this.exited) await Promise.race([this.closed, new Promise(resolve => setTimeout(resolve, 2000))]);
  }

  killGroup(signal) {
    if (!this.child.pid) return;
    try { process.kill(-this.child.pid, signal); }
    catch (error) { if (error.code !== 'ESRCH') this.record('cleanup-error', { message: error.message }); }
  }
}

async function runTask(context, row) {
  const { options, manifest, preflight, agentsBytes, configBytes, cloudBytes, ownedRoot, active } = context;
  const record = manifest.tasks.find(task => task.id === row.id);
  const directory = path.join(options['run-dir'], 'tasks', row.id);
  const worktree = path.join(ownedRoot, row.id);
  const home = path.join(directory, 'home');
  const codexHome = path.join(home, '.codex');
  const temporary = path.join(directory, 'tmp');
  let added = false;
  let rpc;
  let timer;
  let resolveCompletion;
  let rejectCompletion;
  const completion = new Promise((resolve, reject) => { resolveCompletion = resolve; rejectCompletion = reject; });
  completion.catch(() => {});
  const save = () => {
    json(path.join(directory, 'task.json'), record);
    context.save();
  };
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  Object.assign(record, { worktree, prepared_at: new Date().toISOString(), cleanup: 'PENDING' });
  save();
  try {
    ensure(!context.interrupted, 'Run interrupted before task preparation');
    verifyPreflight(preflight);
    ensure(sha256(fs.readFileSync(options['config-template'])) === manifest.config_sha256, 'Config template changed during the run');
    ensure(sha256(fs.readFileSync(options['cloud-skills-snapshot'])) === manifest.cloud_skills_sha256, 'Cloud skills snapshot changed during the run');
    command('git', ['-C', REPOS[row.repo], 'worktree', 'add', '--detach', worktree, manifest.repository_refs[row.repo]]);
    added = true;
    ensure(command('git', ['-C', worktree, 'rev-parse', 'HEAD']) === manifest.repository_refs[row.repo], 'Task worktree commit mismatch');
    const tracked = command('git', ['-C', worktree, 'ls-files', '-z']).split('\0').filter(Boolean);
    json(path.join(directory, 'repository-instructions.json'), tracked.filter(file => /(^|\/)(AGENTS\.md|\.agents\/|\.codex\/)/.test(file)));
    const agentsTarget = path.join(worktree, 'AGENTS.md');
    if (fs.existsSync(agentsTarget)) fs.copyFileSync(agentsTarget, path.join(directory, 'original-AGENTS.md'));
    fs.rmSync(agentsTarget, { force: true });
    fs.writeFileSync(agentsTarget, agentsBytes);
    fs.mkdirSync(codexHome, { recursive: true, mode: 0o700 });
    fs.mkdirSync(temporary, { recursive: true, mode: 0o700 });
    fs.writeFileSync(path.join(codexHome, 'config.toml'), configBytes, { mode: 0o600 });
    const cloudSnapshot = path.join(codexHome, 'cloud-skills.json');
    fs.writeFileSync(cloudSnapshot, cloudBytes, { mode: 0o600 });
    if (options['auth-file']) fs.symlinkSync(options['auth-file'], path.join(codexHome, 'auth.json'));
    const env = isolatedEnvironment(home, codexHome, temporary);
    record.login_status = verifyLogin(directory, worktree, env);
    record.mcp_approval_config = verifyMcpApproval(directory, worktree, env);
    ensure(!context.interrupted, 'Run interrupted before app-server launch');
    rpc = new AppServer(directory, worktree, env, cloudSnapshot, (message, event) => {
      if (message.method === 'runner/failure') {
        const error = new Error(message.params.message);
        error.code = message.params.code;
        rejectCompletion(error);
      }
      const params = message.params;
      if (params?.threadId && record.thread_id && params.threadId !== record.thread_id) return;
      if (['turn/started', 'turn/completed'].includes(message.method) && params?.turn) {
        record.turn_id = params.turn.id;
        record.execution_started = true;
        if (message.method === 'turn/started') { record.status = 'RUNNING'; record.started_at = event.at; save(); }
        else { record.completion = params.turn; resolveCompletion(message); }
      }
      if (params?.item?.type === 'mcpToolCall') {
        fs.appendFileSync(path.join(directory, 'mcp-events.jsonl'), `${JSON.stringify(event)}\n`);
        if (params.item.server !== 'skillfetch') throw new Error(`Unexpected model MCP server: ${params.item.server}`);
      }
      if (/raw.*response|response.*raw/i.test(message.method || '')) record.raw_response_event_count++;
    });
    active.add(rpc);
    record.app_server_pid = rpc.child.pid;
    timer = setTimeout(() => {
      const error = new Error(`Session timeout after ${options['timeout-seconds']} seconds`);
      error.code = 'TIMEOUT';
      rpc.fail(error);
    }, options['timeout-seconds'] * 1000);
    const initialize = await rpc.request('initialize', {
      clientInfo: { name: 'skillfetch_codex_e2e', title: 'skillfetch measured Codex E2E', version: '1.0.0' },
      capabilities: { experimentalApi: true },
    });
    json(path.join(directory, 'initialize.json'), initialize);
    rpc.send({ jsonrpc: '2.0', method: 'initialized', params: {} });
    const account = await rpc.request('account/read', { refreshToken: false });
    json(path.join(directory, 'account-read.json'), account);
    record.auth_mode = account.result?.account?.type || null;
    record.auth_plan_type = account.result?.account?.planType || null;
    ensure(record.auth_mode === 'chatgpt' && record.auth_plan_type === 'pro', 'NOT_RUN: app-server account is not a ChatGPT Pro subscription account');
    const start = await rpc.request('thread/start', {
      cwd: worktree, ephemeral: true, approvalPolicy: 'never', sandbox: 'workspace-write',
      experimentalRawEvents: true, ...(options.model ? { model: options.model } : {}),
    });
    json(path.join(directory, 'thread-start.json'), start);
    const thread = start.result?.thread;
    ensure(thread?.id && thread.ephemeral === true, 'Expected a fresh ephemeral thread');
    verifyRuntimeIdentity(start.result, account.result.account);
    ensure(start.result.approvalPolicy === 'never', 'Effective approval policy is not never');
    ensure(start.result.sandbox?.type === 'workspaceWrite' && start.result.sandbox.networkAccess === false,
      'Expected workspace-write sandbox with tool network access disabled');
    ensure((start.result.modelProvider || thread.modelProvider) === 'openai', 'Unexpected model provider; subscription authentication cannot be established');
    Object.assign(record, {
      thread_id: thread.id, model: start.result.model || thread.model,
      model_provider: start.result.modelProvider || thread.modelProvider,
      cli_version: thread.cliVersion, reasoning_effort: start.result.reasoningEffort,
    });
    if (context.recovery) {
      const actualModel = { model: record.model, model_provider: record.model_provider, reasoning_effort: record.reasoning_effort ?? null };
      ensure(canonical(actualModel) === canonical(context.recovery.expected_model), 'Effective model configuration differs from the original run');
    }
    await awaitMcpConnected(rpc, thread.id, directory);
    record.mcp_preflight = 'PASS';
    ensure(!context.interrupted && !rpc.fatal, 'Session stopped before turn/start');
    // Persist the single submission before writing to the transport. Never retry it.
    Object.assign(record, { status: 'TURN_START_REQUESTED', turn_start_requested: true, turn_start_requested_at: new Date().toISOString() });
    save();
    const turn = await rpc.request('turn/start', { threadId: thread.id, input: [{ type: 'text', text: row.prompt }] });
    json(path.join(directory, 'turn-start.json'), turn);
    ensure(turn.result?.turn?.id, 'turn/start returned no turn ID');
    record.turn_id = turn.result.turn.id;
    record.execution_started = true;
    save();
    const completed = await completion;
    json(path.join(directory, 'turn-completed.json'), completed);
    record.status = completed.params.turn.status === 'completed' ? 'COMPLETED' : completed.params.turn.status.toUpperCase();
  } catch (error) {
    record.error = { message: error.message, code: error.code || 'ERROR' };
    record.status = record.turn_start_requested ? (['TIMEOUT', 'INTERRUPTED', 'USER_INPUT_REQUIRED'].includes(error.code) ? error.code : 'FAILED_AFTER_START_REQUEST') : 'NOT_RUN';
  } finally {
    clearTimeout(timer);
    if (rpc) {
      if (record.turn_start_requested && !record.completion && record.thread_id && record.turn_id && !rpc.exited) {
        try { await rpc.request('turn/interrupt', { threadId: record.thread_id, turnId: record.turn_id }, 5000, true); }
        catch (error) { record.interrupt_error = error.message; }
      }
      await rpc.close();
      active.delete(rpc);
    }
    try {
      if (options['auth-file'] && fs.existsSync(codexHome)) fs.rmSync(path.join(codexHome, 'auth.json'), { force: true });
      if (added) {
        ensure(path.dirname(worktree) === ownedRoot && path.basename(worktree) === row.id, 'Refusing cleanup outside the owned worktree');
        command('git', ['-C', REPOS[row.repo], 'worktree', 'remove', '--force', worktree]);
      }
      record.cleanup = 'DONE';
    } catch (error) { record.cleanup = 'FAILED'; record.cleanup_error = error.message; }
    record.finished_at = new Date().toISOString();
    save();
    process.stdout.write(`${row.id}: ${record.status}; cleanup=${record.cleanup}\n`);
  }
}

async function main(argv) {
  const options = parseArgs(argv);
  if (options.help) { process.stdout.write(HELP); return; }
  ensure(!fs.existsSync(options['run-dir']), 'Run directory already exists; refusing possible duplicate measured tasks');
  const tasksBytes = fs.readFileSync(TASKS);
  const allRows = readTasks(tasksBytes);
  const agentsBytes = fs.readFileSync(options['agents-file']);
  ensure(agentsBytes.length > 0, 'AGENTS file is empty');
  const configBytes = fs.readFileSync(options['config-template']);
  const approvalConfig = verifyApprovalConfig(configBytes);
  const cloudBytes = fs.readFileSync(options['cloud-skills-snapshot']);
  const cloudSnapshot = JSON.parse(cloudBytes);
  ensure(Array.isArray(cloudSnapshot.skills) && cloudSnapshot.skills.length === 0, 'Cloud skills snapshot must contain an empty skills array');
  const preflight = JSON.parse(fs.readFileSync(options['source-preflight'], 'utf8'));
  verifyPreflight(preflight);
  ensure(configBytes.toString('utf8').includes(preflight.source_path) && configBytes.toString('utf8').includes(preflight.index_path),
    'Config template must reference the preflighted source and index paths');
  if (options['auth-file']) ensure(fs.statSync(options['auth-file']).isFile(), 'Auth path is not a file');
  const version = command(CODEX, ['--version']);
  ensure(version === 'codex-cli 0.164.0', 'NOT_RUN: CLI must be exactly 0.164.0');
  ensure(!options.model || options.model === 'gpt-6-astra', 'NOT_RUN: model override must be gpt-6-astra');
  const identity = {
    source_commit: SOURCE_COMMIT, codex_version: version, tasks_sha256: sha256(tasksBytes),
    agents_sha256: sha256(agentsBytes), config_sha256: sha256(configBytes), cloud_skills_sha256: sha256(cloudBytes),
    timeout_seconds: options['timeout-seconds'],
  };
  const recovery = loadRecovery(options, allRows, identity, preflight);
  const rows = recovery ? recovery.rows : allRows;
  const refs = recovery ? recovery.repository_refs : Object.fromEntries(Object.entries(REPOS).map(([name, repo]) => [name,
    command('git', ['-C', repo, 'rev-parse', '--verify', 'refs/heads/s5^{commit}'])]));
  for (const [name, repo] of Object.entries(REPOS)) ensure(
    command('git', ['-C', repo, 'rev-parse', '--verify', `${refs[name]}^{commit}`]) === refs[name], `Pinned commit unavailable: ${name}`);
  fs.mkdirSync(path.dirname(options['run-dir']), { recursive: true });
  fs.mkdirSync(options['run-dir'], { mode: 0o700 });
  const ownedRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'skillfetch-codex-e2e-owned-'));
  const manifest = {
    schema_version: 1, created_at: new Date().toISOString(), status: 'RUNNING',
    ...identity, repository_refs: refs, tasks_path: TASKS, inference_explicitly_allowed: true,
    concurrency: options.concurrency, requested_model: options.model || null,
    mcp_approval_config: approvalConfig,
    recovery_of: recovery ? { directory: recovery.directory, manifest_sha256: recovery.manifest_sha256, expected_model: recovery.expected_model, evidence: recovery.evidence } : null,
    assistant_round_cap: null, experimental_raw_events_requested: true,
    owned_worktree_root: ownedRoot,
    tasks: rows.map(row => ({ id: row.id, repo: row.repo, prompt_sha256: sha256(row.prompt), status: 'NOT_RUN', turn_start_requested: false, execution_started: false, raw_response_event_count: 0 })),
  };
  const context = { options, manifest, preflight, agentsBytes, configBytes, cloudBytes, ownedRoot, recovery, active: new Set(), interrupted: null,
    save: () => json(path.join(options['run-dir'], 'manifest.json'), manifest) };
  context.save();
  fs.writeFileSync(path.join(options['run-dir'], 'tasks.jsonl'), tasksBytes);
  fs.writeFileSync(path.join(options['run-dir'], 'AGENTS.input.md'), agentsBytes);
  fs.writeFileSync(path.join(options['run-dir'], 'config.input.toml'), configBytes, { mode: 0o600 });
  fs.writeFileSync(path.join(options['run-dir'], 'cloud-skills.input.json'), cloudBytes, { mode: 0o600 });
  json(path.join(options['run-dir'], 'source-preflight.json'), preflight);
  const onSignal = signal => {
    context.interrupted = signal;
    for (const rpc of context.active) {
      const error = new Error(`Received ${signal}`);
      error.code = 'INTERRUPTED';
      rpc.fail(error);
    }
  };
  const sigint = () => onSignal('SIGINT');
  const sigterm = () => onSignal('SIGTERM');
  process.on('SIGINT', sigint);
  process.on('SIGTERM', sigterm);
  let next = 0;
  try {
    reserveRecovery(recovery, options['run-dir']);
    const lanes = await Promise.allSettled(Array.from({ length: options.concurrency }, async () => {
      while (!context.interrupted && next < rows.length) await runTask(context, rows[next++]);
    }));
    const failures = lanes.filter(lane => lane.status === 'rejected');
    if (failures.length) manifest.runner_errors = failures.map(lane => String(lane.reason));
  } catch (error) {
    manifest.runner_errors = [...(manifest.runner_errors || []), String(error)];
    throw error;
  } finally {
    await Promise.all([...context.active].map(rpc => rpc.close()));
    process.off('SIGINT', sigint);
    process.off('SIGTERM', sigterm);
    try { fs.rmdirSync(ownedRoot); } catch (error) { manifest.worktree_root_cleanup_error = error.message; }
    manifest.finished_at = new Date().toISOString();
    manifest.status = context.interrupted ? 'INTERRUPTED' : manifest.tasks.every(task => task.status === 'COMPLETED' && task.cleanup === 'DONE') ? 'COMPLETED' : 'COMPLETED_WITH_FAILURES';
    context.save();
    if (manifest.status !== 'COMPLETED') process.exitCode = context.interrupted ? 130 : 1;
  }
}

module.exports = { AppServer, parseArgs, readTasks, validateMcp, awaitMcpConnected, loadRecovery, reserveRecovery, verifyFiles, verifyPreflight, isolatedEnvironment, verifyLogin, verifyApprovalConfig, verifyMcpApproval, verifyRuntimeIdentity };
if (require.main === module) main(process.argv.slice(2)).catch(error => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
