#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { isDeepStrictEqual } = require('node:util');
const { aggregateMetrics, readLabelBasis, joinLabels } = require('./codex-e2e-3-extract.cjs');
const REPLICATES = ['r1', 'r2', 'r3'];
const ORACLE_SHA = '7db50e73c7dfd6b0b810ba65231fd1475a25a563651310592c88da23795e108c';
const AGENTS_SHA = '4cdfac9064f4f6dda0846dff9c8fe52a90dd2e65ba09cc494c735ea9c83bfa8a';
const SOURCE_COMMIT = '14d2020f1275e10a272eb46575c9bd6d4a2182e4';
const HELP = 'Usage: node codex-e2e-3-render.cjs --run-root DIR [--out NEW_REPORT.md] [--check]\nRequires finished manifests, observations-e2e3.json, hash-bound audit-verification.json, child-agent-findings.json, and independent-metrics-verification.json.\nAudit FAIL is retained in a failure report; only PASS permits a completion claim.\nWrites a new report and 57 query-records/<replicate>/<task>.json files; never overwrites.\n--check validates and renders in memory only. --self-test runs offline tests without writing files.\n';
const ensure = (ok, message) => { if (!ok) throw new Error(message); };
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const code = value => '`' + String(value ?? '미확인').replaceAll('`', '\\`').replaceAll('|', '\\|').replaceAll('\n', ' ') + '`';
const escaped = value => String(value).replaceAll('|', '\\|').replaceAll('\n', '<br>');
const percent = value => value === null || value === undefined ? 'N/A' : `${(value * 100).toFixed(1)}%`;
const ratio = (n, d) => `${n}/${d} (${d ? percent(n / d) : 'N/A'})`;
const rate = value => ratio(value.numerator, value.denominator);
const count = (values, predicate) => values.filter(predicate).length;
const countText = values => Object.entries(values).map(([key, value]) => `${code(key)} ${value}`).join(', ') || '없음';

function validateCompletion({ manifest, audit, replicates, sessions }) {
  const terminal = ['COMPLETED', 'COMPLETED_WITH_FAILURES', 'FAILED', 'INTERRUPTED'];
  ensure(terminal.includes(manifest.status) && manifest.finished_at, 'Root manifest is not terminal');
  ensure(['PASS', 'FAIL'].includes(audit.status), 'A finished audit is required');
  ensure(audit.totals?.recorded_slots === 57, 'Audit must retain all 57 session slots');
  ensure(sessions.length === 57 && new Set(sessions.map(s => s.session_key)).size === 57, 'Exactly 57 unique session records are required');
  ensure(isDeepStrictEqual(replicates.map(r => r.id), REPLICATES), 'Three replicate manifests are required');
  for (const replicate of replicates) {
    ensure(terminal.includes(replicate.manifest.status) && replicate.manifest.finished_at, `Replicate ${replicate.id} is not terminal`);
    const selected = sessions.filter(s => s.replicate === replicate.id);
    ensure(selected.length === 19 && new Set(selected.map(s => s.task_id)).size === 19, `Expected 19 task records in ${replicate.id}`);
  }
}

function firstCycle(call) {
  if (call?.model_response_cycle == null) return '미확인';
  return `${call.model_response_cycle} (${call.model_response_cycle_mapping === 'direct_call_id' ? '직접 연결' : '추론'})`;
}

function returnedIds(ids) { return ids == null ? '미확인(null)' : ids.length ? ids.map(code).join('<br>') : '`[]`'; }

function primaryEndings(session) {
  return session.turn_end_events.filter(event => event.turn?.id === session.manifest.turn_id).map(event => event.turn.status ?? 'UNKNOWN').join(', ') || '미관측';
}

function assertHash(file, expected, label = file) {
  const actual = sha(fs.readFileSync(file));
  ensure(actual === expected, `Evidence changed: ${label}`);
  return actual;
}

function loadEvidence(runRoot) {
  const root = fs.realpathSync(runRoot);
  const manifestFile = path.join(root, 'manifest.json');
  const auditFile = path.join(root, 'audit-verification.json');
  const observationFile = path.join(root, 'observations-e2e3.json');
  const manifest = read(manifestFile), audit = read(auditFile), observation = read(observationFile);
  ensure(observation.schema_version === 3 && observation.run_root === root && audit.run_root === root, 'Evidence schema or run root mismatch');
  assertHash(manifestFile, audit.manifest_sha256);
  assertHash(path.join(__dirname, 'codex-e2e-3-verify.cjs'), audit.auditor_sha256);
  ensure(observation.sources.runs.length === 3, 'Expected three observation sources');
  const replicates = REPLICATES.map(id => {
    const source = observation.sources.runs.find(r => r.replicate === id);
    ensure(source && source.run_directory === path.join(root, id), `Wrong replicate source: ${id}`);
    assertHash(source.manifest.file, source.manifest.sha256);
    assertHash(source.observations_file, source.observations_sha256);
    const measured = read(source.observations_file);
    const replicateManifest = read(source.manifest.file);
    ensure(measured.source_evidence_kind === 'MEASURED_MODEL_RUN' || measured.source_evidence_kind === null, `Synthetic or unrecognized evidence: ${id}`);
    return { id, manifest: replicateManifest, measured, source };
  });
  const sessions = observation.sessions.codex;
  validateCompletion({ manifest, audit, replicates, sessions });
  ensure(observation.sessions.claude_v2.length === 57, 'Expected 57 existing Claude V2 sessions');
  ensure(observation.task_sets.length === 19 && observation.request_lengths.length === 19, 'Expected 19 comparison tasks');
  ensure(observation.label_basis.related_task_count === 17 && observation.label_basis.no_related_task_count === 2 && observation.label_basis.oracle.sha256 === ORACLE_SHA, 'Wrong corrected oracle or task denominator');
  assertHash(observation.label_basis.oracle.file, ORACLE_SHA);
  assertHash(observation.label_basis.basis.file, observation.label_basis.basis.sha256);
  const labels = readLabelBasis(observation.label_basis.basis.file);
  for (const source of [observation.sources.extractor, observation.sources.reused_extractor, observation.sources.claude_v2]) assertHash(source.file, source.sha256);
  for (const [cohort, cohortSessions] of Object.entries(observation.sessions)) {
    for (const session of cohortSessions) {
      for (const [key, expected] of Object.entries(joinLabels(session.task_id, session.loaded_skill_ids, labels.rows))) ensure(isDeepStrictEqual(session[key], expected), `Corrected oracle join differs: ${cohort}/${session.session_key}/${key}`);
    }
    ensure(isDeepStrictEqual(aggregateMetrics(cohortSessions), observation.metrics[cohort].pooled), `Pooled metrics mismatch: ${cohort}`);
    for (const replicate of REPLICATES) ensure(isDeepStrictEqual(aggregateMetrics(cohortSessions.filter(s => s.replicate === replicate)), observation.metrics[cohort].per_replicate[replicate]), `Replicate metrics mismatch: ${cohort}/${replicate}`);
  }
  for (const session of sessions) {
    const task = session.manifest;
    const replicate = replicates.find(r => r.id === session.replicate);
    const sourceTask = replicate.measured.tasks.find(t => t.id === session.task_id);
    ensure(sourceTask && isDeepStrictEqual(sourceTask.manifest, task) && isDeepStrictEqual(sourceTask.evidence.transcript_present ? sourceTask.returned_skill_ids : null, session.loaded_skill_ids) && isDeepStrictEqual(sourceTask.search_calls, session.search_calls), `Session differs from source observation: ${session.session_key}`);
    const auditedTask = audit.tasks.find(t => t.replicate === session.replicate && t.id === session.task_id);
    ensure(auditedTask, `Missing audited session: ${session.session_key}`);
    if (auditedTask.transcript_sha256) assertHash(session.evidence.transcript, auditedTask.transcript_sha256, session.session_key);
    for (const [key, value] of Object.entries({ cli_version: '0.164.0', model: 'gpt-6-astra', reasoning_effort: 'medium', auth_mode: 'chatgpt', auth_plan_type: 'pro' })) {
      ensure(task[key] == null || task[key] === value, `Unexpected observed identity ${key}: ${session.session_key}`);
    }
  }
  for (const replicate of replicates) {
    ensure(replicate.manifest.source_commit === SOURCE_COMMIT && replicate.manifest.agents_sha256 === AGENTS_SHA, `Wrong source/router pin: ${replicate.id}`);
    const audited = audit.replicates.find(r => r.id === replicate.id);
    ensure(audited?.manifest_sha256 === replicate.source.manifest.sha256, `Replicate audit hash mismatch: ${replicate.id}`);
  }
  const oldClaude = read(observation.sources.claude_v2.file);
  for (const session of observation.sessions.claude_v2) {
    const old = oldClaude.sessions.find(s => s.task_id === session.task_id && s.tag === session.replicate);
    ensure(old && isDeepStrictEqual(old.loaded_skill_ids, session.loaded_skill_ids), `Existing Claude returned IDs differ: ${session.session_key}`);
  }
  for (const [key, input] of Object.entries(manifest.inputs)) assertHash(input.snapshot_path, input.sha256, key);
  ensure(manifest.inputs.agents.sha256 === AGENTS_SHA, 'Full router hash mismatch');
  const configFile = manifest.inputs.config.snapshot_path;
  const config = fs.readFileSync(configFile, 'utf8');
  ensure(fs.readFileSync(configFile).equals(fs.readFileSync(path.join(__dirname, 'codex-e2e-2-preparation/config-template.toml'))), 'MCP/config policy differs from approved v2');
  const sourcePreflight = read(manifest.inputs.source_preflight.snapshot_path);
  ensure(sourcePreflight.source_commit === SOURCE_COMMIT && sourcePreflight.status === 'PASS', 'Source fingerprint preflight failed');
  const preparation = read(path.join(__dirname, 'codex-e2e-3-preparation/preparation.json'));
  const oldReports = Object.entries(preparation.old_report_hashes).map(([name, expected]) => ({ file: path.join(__dirname, name), sha256: assertHash(path.join(__dirname, name), expected) }));
  const prompts = new Map(fs.readFileSync(manifest.inputs.tasks.snapshot_path, 'utf8').trimEnd().split('\n').map(line => { const task = JSON.parse(line); return [task.id, task.prompt]; }));
  ensure(prompts.size === 19, 'Frozen prompt count mismatch');
  for (const session of sessions) ensure(/^[A-Za-z0-9_-]+$/.test(session.task_id) && prompts.has(session.task_id) && session.session_key === `${session.replicate}/${session.task_id}`, 'Invalid session key or output path');
  const identityVerified = sessions.filter(session => {
    const task = session.manifest, keyChecks = task.login_status?.api_key_environment_absent;
    return task.cli_version === '0.164.0' && task.model === 'gpt-6-astra' && task.reasoning_effort === 'medium' && task.auth_mode === 'chatgpt' && task.auth_plan_type === 'pro' && task.login_status?.chatgpt === true && keyChecks && Object.keys(keyChecks).length >= 8 && Object.values(keyChecks).every(v => v === true);
  }).length;
  const independentFile = path.join(root, 'independent-metrics-verification.json');
  const independent = read(independentFile);
  ensure(independent.status === 'PASS' && independent.oracle_sha256 === ORACLE_SHA && independent.observations_sha256 === sha(fs.readFileSync(observationFile)), 'Independent metrics verification is missing, failed, or stale');
  ensure(independent.sessions === sessions.length && independent.rows.length === sessions.length && new Set(independent.rows.map(row => `${row.rep}/${row.task_id}`)).size === sessions.length, 'Independent metrics session set differs');
  const pooled = observation.metrics.codex.pooled;
  ensure(independent.prompt_exact === pooled.prompt_submission_checks.exact_matches && independent.query4_exact === pooled.query_check_status_counts.PASS, 'Independent prompt/query verification differs');
  for (const replicate of [...REPLICATES, 'pooled']) {
    const measured = replicate === 'pooled' ? pooled : observation.metrics.codex.per_replicate[replicate];
    const expected = { sessions: measured.selected_sessions, hit_n: measured.hit_loaded_related.numerator, hit_d: measured.hit_loaded_related.denominator,
      R: measured.returned_ids.relevant, N: measured.returned_ids.graded_below_2, U: measured.returned_ids.ungraded,
      micro: measured.precision_graded_micro.value, macro: measured.precision_graded_macro.value, macro_d: measured.precision_graded_macro.session_denominator,
      none_loaded: measured.none_task_loading.loaded_sessions, none_total: measured.none_task_loading.selected_sessions, calls: measured.server_call_observations.total_calls };
    ensure(isDeepStrictEqual(independent.metrics[replicate], expected), `Independent metrics differ: ${replicate}`);
  }
  for (const row of independent.rows) {
    const session = sessions.find(item => item.session_key === `${row.rep}/${row.task_id}`);
    ensure(session && isDeepStrictEqual(row.ids, session.loaded_skill_ids) && row.R === session.relevance_counts.relevant && row.N === session.relevance_counts.graded_below_2 && row.U === session.relevance_counts.ungraded && row.related === session.oracle_related && row.calls === session.skillfetch_call_count, `Independent session observation differs: ${row.rep}/${row.task_id}`);
    assertHash(session.evidence.transcript, row.transcript_sha256);
  }
  const childFile = path.join(root, 'child-agent-findings.json');
  const childFindings = read(childFile);
  ensure(childFindings.schema_version === 1 && childFindings.run_root === root && childFindings.audit.path === auditFile && childFindings.audit.status === audit.status && childFindings.audit.passed === audit.passed && childFindings.audit.checked === audit.checked && childFindings.audit.unchanged === true, 'Child findings do not match the immutable runtime audit');
  assertHash(auditFile, childFindings.audit.sha256);
  ensure(childFindings.primary_sessions_scanned === sessions.length && childFindings.primary_turn_start_count === audit.totals.observed_turn_start_count && childFindings.primary_turn_completed_count === count(sessions, s => s.result_status === 'COMPLETED'), 'Child scan primary counts differ');
  ensure(childFindings.scans.length === sessions.length && new Set(childFindings.scans.map(row => `${row.replicate}/${row.task_id}`)).size === sessions.length, 'Child scan session set differs');
  for (const scan of childFindings.scans) {
    const session = sessions.find(item => item.session_key === `${scan.replicate}/${scan.task_id}`);
    ensure(session && scan.controller_turn_start_count === session.prompt_submission.count, 'Child scan primary submission differs');
    assertHash(session.evidence.transcript, scan.transcript_sha256);
  }
  const children = new Set(childFindings.scans.flatMap(scan => scan.observed_child_thread_ids));
  ensure(childFindings.attempts.length === childFindings.spawn_agent_call_count && childFindings.scans.reduce((total, scan) => total + scan.spawn_agent_call_count, 0) === childFindings.spawn_agent_call_count && count(childFindings.attempts, item => item.outcome === 'FAILED_BEFORE_OBSERVED_CHILD') === childFindings.failed_spawn_agent_call_count, 'Child spawn attempt counts differ');
  ensure(children.size === childFindings.child_thread_count && childFindings.findings.length === children.size && childFindings.unique_observed_runtime_threads === childFindings.unique_primary_threads + children.size, 'Observed child thread counts differ');
  for (const finding of childFindings.findings) {
    ensure(children.has(finding.child.thread_id) && childFindings.attempts.some(attempt => attempt.call_id === finding.spawn_call_id && attempt.observed_child_thread_ids.includes(finding.child.thread_id)), 'Child finding has no matching spawn');
    assertHash(finding.transcript.path, finding.transcript.sha256);
  }
  ensure(!children.size || audit.status === 'FAIL', 'Unexpected children must not be presented as runtime audit PASS');
  return { root, manifestFile, auditFile, observationFile, manifest, audit, observation, replicates, sessions, config, configFile, sourcePreflight, oldReports, prompts, identityVerified, independentFile, independent, childFile, childFindings };
}

function queryArtifacts(evidence) {
  const observationSha = sha(fs.readFileSync(evidence.observationFile));
  return evidence.sessions.map(session => {
    const length = evidence.observation.request_lengths.find(row => row.task_id === session.task_id);
    const prompt = evidence.prompts.get(session.task_id);
    ensure(typeof prompt === 'string' && sha(prompt) === length.prompt_sha256, `Frozen query prompt mismatch: ${session.session_key}`);
    return { file: path.join(evidence.root, 'query-records', session.replicate, `${session.task_id}.json`),
      value: { schema_version: 1, session_key: session.session_key, source_observation_file: evidence.observationFile,
        source_observation_sha256: observationSha, replicate_observation_file: session.observation_file,
        replicate_observation_json_pointer: session.observation_json_pointer, transcript: session.evidence.transcript,
        original_frozen_prompt: prompt, prompt_length: length, prompt_submission: session.prompt_submission,
        search_calls: session.search_calls } };
  });
}

function renderReport(evidence, target) {
  const { root, manifest, audit, observation: obs, sessions, replicates, sourcePreflight, childFindings: child } = evidence;
  const link = (label, file) => `[${escaped(label)}](${path.relative(path.dirname(target), file).split(path.sep).map(encodeURIComponent).join('/')})`;
  const lines = [], add = (...text) => lines.push(...text);
  const metrics = obs.metrics.codex;
  const fullTasks = replicates.flatMap(r => r.measured.tasks.map(t => ({ ...t, replicate: r.id })));
  const calls = sessions.flatMap(s => s.call_summaries.map(c => ({ ...c, session: s })));
  const loads = sessions.flatMap(s => s.load_calls.map(c => ({ ...c, session: s })));
  const searches = sessions.flatMap(s => s.search_calls.map(c => ({ ...c, session: s })));
  const queryLink = session => link('queries 원문 JSON', path.join(root, 'query-records', session.replicate, `${session.task_id}.json`));
  const observationLink = session => `${link('관찰 JSON', session.observation_file)} ${code(session.observation_json_pointer)}`;
  add(`Codex CLI 0.164.0 | 모델: gpt-6-astra (reasoning: medium) | 인증: ChatGPT Pro 구독 로그인 (\`chatgpt\`/\`pro\`), API 키 환경변수 미상속 | 주 세션 실제 신원·키 부재 확인 ${evidence.identityVerified}/57`, '',
    '# Codex E2E 3: 전체 skillfetch 라우터, 19개 태스크 × 3회', '',
    `**${audit.status === 'PASS' && manifest.status === 'COMPLETED' ? '완료 · 실행·증거 감사 PASS' : 'FAIL · 완료 판정 불가'}: ${audit.passed}/${audit.checked}개 감사 검사 통과.** manifest=${code(manifest.status)}, audit=${code(audit.status)}. 관측된 실제 태스크 제출 ${audit.totals.observed_turn_start_count ?? '미확인'}/57회, 정상 종료 ${count(sessions, s => s.result_status === 'COMPLETED')}/57회다. 발화율은 **${ratio(metrics.pooled.skillfetch_called_sessions, 57)}**다. 발화는 모델이 skillfetch MCP 호출을 요청한 세션이며, 응답 수신·프로토콜 성공·스킬 반환과 별도로 센다.`, '',
    `**실제 실행 범위: 주 세션 ${child.primary_sessions_scanned}개 + 예상하지 않은 native 하위 에이전트 ${child.child_thread_count}개.** 관측된 고유 thread/turn은 ${child.unique_observed_runtime_threads}/${child.unique_observed_runtime_turns}개다. 모델의 spawn_agent 시도 ${child.spawn_agent_call_count}회 중 ${child.failed_spawn_agent_call_count}회는 부모 rollout 누락 오류였고, ${child.child_thread_count}개 하위 thread가 실제 실행됐다. 설정의 multi_agent=false·multi_agent_v2=false가 이 실행에서 하위 에이전트를 막지 못했다. 초기 skillfetch 라우팅 이후 발생한 이 동작 때문에 주 세션 종료 성공과 별개로 런타임 감사 FAIL을 유지한다. 재실행하지 않았다.`, '',
    `${link('종료 manifest', evidence.manifestFile)} · ${link('독립 전수 감사', evidence.auditFile)} · ${link('통합 관찰·새 라벨 결합', evidence.observationFile)} · ${link('별도 원시 파서의 지표 재검증', evidence.independentFile)} (${code(evidence.independent.status)})`, '',
    `${link('하위 에이전트 전수 조사·원시 이벤트 참조', evidence.childFile)}. 하위 에이전트 MCP 이벤트는 ${child.findings.reduce((total, finding) => total + finding.tool_usage.mcp_event_count, 0)}개이며, 아래 ${calls.length}회 MCP 지표는 57개 주 세션의 호출이다. 하위 에이전트의 독립 인증·프로세스 정리는 확인되지 않았다.`, '',
    '고정된 동일 19개 요청을 세 번 반복하는 57개 주 세션을 대상으로 했다. 아래 발화·질의·프로토콜·로드·관련성 지표의 분모는 이 주 세션이며, 하위 에이전트를 별도 태스크 표본으로 추가하지 않았다. 실제 제출·종료 수와 실패는 아래 기록한다. 이번 변경은 AGENTS.md에 `When`, 1–8단계, `Rules`를 모두 넣은 것이다. Codex 호스트용 1–2단계는 이전 승인본과 같고, 로컬 스킬 예시만 `.agents/skills/`로 바꿨다. 코드 결과물의 품질이나 테스트 통과 여부는 채점하지 않았다.', '',
    '## 주 세션의 실제 실행과 호출', '',
    '| 지표 | r1 | r2 | r3 | 합계 |', '|---|---:|---:|---:|---:|');
  const groups = [...REPLICATES.map(r => ({ sessions: sessions.filter(s => s.replicate === r), metrics: metrics.per_replicate[r] })), { sessions, metrics: metrics.pooled }];
  const metricRow = (label, value) => add(`| ${label} | ${groups.map(g => value(g)).join(' | ')} |`);
  metricRow('실제 요청 제출', g => `${g.metrics.prompt_submission_checks.observed_turn_start_count}/${g.sessions.length}`);
  metricRow('skillfetch 호출 세션(발화율)', g => ratio(g.metrics.skillfetch_called_sessions, g.sessions.length));
  metricRow('서버 결과 수신 세션', g => ratio(count(g.sessions, s => s.server_result_count > 0), g.sessions.length));
  metricRow('MCP 프로토콜 성공 응답 세션', g => ratio(count(g.sessions, s => s.successful_server_call_count > 0), g.sessions.length));
  metricRow('search 호출 세션 / 횟수', g => `${g.metrics.searched_sessions}/${g.sessions.length} · ${g.metrics.query_checks_observed}회`);
  metricRow('queries 4개·4번째 원문 완전 일치', g => `${g.metrics.query_check_status_counts.PASS || 0}/${g.metrics.query_checks_observed} 검색 호출`);
  metricRow('load 호출 세션 / 횟수', g => `${count(g.sessions, s => s.load_calls.length > 0)}/${g.sessions.length} · ${g.metrics.load_call_count}회`);
  metricRow('실제 스킬 ID 반환 세션', g => ratio(g.metrics.loaded_sessions, g.sessions.length));
  metricRow('반환 세트 미확인(null)', g => g.metrics.ambiguous_return_sessions);
  metricRow('정상 turn 종료', g => `${count(g.sessions, s => s.result_status === 'COMPLETED')}/${g.sessions.length}`);
  metricRow('worktree 정리 DONE', g => `${count(g.sessions, s => s.manifest.cleanup === 'DONE')}/${g.sessions.length}`);
  add('', `주 세션의 MCP 요청 ${calls.length}회, 서버 결과 수신 ${metrics.pooled.server_call_observations.received_result}회, 프로토콜 성공 ${metrics.pooled.server_call_observations.protocol_success}회, 승인 거절 ${metrics.pooled.server_call_observations.approval_denied}회다. 서버 결과가 존재해도 MCP 오류 플래그나 도메인 payload 오류가 있으면 성공과 구분한다.`, '',
    '| MCP 도구 | 모델 호출 요청 | 서버 결과 수신 | 프로토콜 SUCCESS | FAILURE | CONFLICT·UNOBSERVED 등 |', '|---|---:|---:|---:|---:|---:|');
  for (const tool of [...new Set(calls.map(c => c.tool))].sort()) {
    const selected = calls.filter(c => c.tool === tool);
    add(`| ${code(tool)} | ${selected.length} | ${count(selected, c => c.server_result_received === true)} | ${count(selected, c => c.protocol_status === 'SUCCESS')} | ${count(selected, c => c.protocol_status === 'FAILURE')} | ${count(selected, c => !['SUCCESS', 'FAILURE'].includes(c.protocol_status))} |`);
  }
  add('', `load payload 의미 상태: ${countText(metrics.pooled.load_semantic_status_counts)}. 반환 관찰 충돌 ${metrics.pooled.load_return_conflicts}회. ` +
    '`SUCCESS`는 skills 배열과 오류 상태에 대한 추출기 판정이고, `PARTIAL_ERROR`는 일부 스킬 반환과 payload errors가 함께 있는 상태다. 반환 ID는 요청 ID가 아니라 프로토콜 성공 결과의 `skills[].id`에서 가져왔다. 충돌한 반환 세트는 null로 남겼다.', '',
    `첫 호출 회차 분포: ${countText(metrics.pooled.first_call_model_response_cycle.cycle_counts)}. 연결 방법: ${countText(metrics.pooled.first_call_model_response_cycle.mapping_counts)}. 회차 미확인 ${metrics.pooled.first_call_model_response_cycle.unknown_sessions}개.`, '',
    '외부 사용자 요청은 주 세션마다 1회 제출했다. 여기서 첫 호출 “회차”는 같은 주 thread/turn의 고유 `rawResponse/completed.responseId` 경계를 센 1-based 모델 응답 순서다. `direct_call_id`는 직접 연결이며, `unique_closed_code_exec_interval` 등은 호출을 감싼 exec 구간으로 추론한 값이다. 추론을 실제 부모 ID로 취급하지 않는다. 불명확하면 미확인으로 남겼다. Claude의 assistant-message 순번과 같은 단위로 비교하지 않는다.', '',
    '## queries 원문과 800자 이상 요청', '',
    '매 검색 호출의 모든 lifecycle 인자 관찰에 대해 `queries.length === 4`, 네 값이 모두 문자열, `queries[3] === 고정 태스크 prompt`를 검사했다. 공백·줄바꿈·Unicode를 정규화하지 않았다. 네 번째 질의뿐 아니라 네 질의 원문, 관찰 sequence, 충돌 여부를 아래 57개 세션의 JSON 링크에 보존했다. 미호출·인자 없음·충돌은 일치로 세지 않는다.', '',
    `800자 이상은 원래 요청의 Unicode code point 수로 판정했다(UTF-16 길이·UTF-8 바이트도 JSON에 보존). 해당 태스크 ${obs.long_request_task_ids.length}/19개, 반복 세션 ${obs.long_request_task_ids.length * 3}/57개다.`, '',
    '| 태스크 | 원문 문자 수 | 800자 이상 | r1 검색 일치/호출 | r2 | r3 |', '|---|---:|---|---|---|---|');
  for (const length of obs.request_lengths) {
    const results = REPLICATES.map(r => {
      const session = sessions.find(s => s.task_id === length.task_id && s.replicate === r);
      return `${session.search_calls.length ? `${count(session.search_calls, c => c.query_check_status === 'PASS')}/${session.search_calls.length}` : '미호출'} · ${queryLink(session)}`;
    });
    add(`| ${length.task_id} | ${length.characters} | ${length.at_least_800 ? '예' : '아니오'} | ${results.join(' | ')} |`);
  }
  add('', '## 관련성: 누적 4-0 oracle로 양쪽을 다시 결합', '',
    `${link('누적 oracle-4-0.jsonl', obs.label_basis.oracle.file)} SHA256: ${code(obs.label_basis.oracle.sha256)}. ${link('판정 기준', obs.label_basis.basis.file)}. 태스크 ID와 revision을 포함한 전체 skill ID가 정확히 일치할 때만 기존 grade를 사용했다. grade ≥ 2를 관련 스킬로 본다. 관련 스킬이 있는 태스크는 17개, 없는 태스크는 2개(${obs.label_basis.no_related_task_ids.map(code).join(', ')})다. 신규 채점은 수행하지 않았다.`, '',
    'hit 분모는 **관련 스킬이 존재하는 태스크에서 실제 스킬을 반환받은 세션**이다. 세 반복이 모두 로드되어도 최대 51이며, 전체 57이나 무조건 51을 분모로 넣지 않았다. R=0이고 미채점 U>0인 세션은 미해결로 따로 센다. 이때 확인된 hit 비율은 하한이며, 미해결을 확정 실패로 바꾸지 않는다.', '',
    'R은 grade ≥ 2, N은 grade < 2, U는 미채점·pool 외 ID다. graded micro precision은 전체 세션의 R 합계/(R+N) 합계다. graded macro precision은 한 개 이상의 채점된 반환이 있는 각 세션의 R/(R+N)을 동일 가중 평균한 값이며, 그 세션 수를 별도 표시한다. U는 0점으로 치환하지 않는다. 동일 ID는 한 세션 안에서 중복 제거하고, 서로 다른 세션에서는 각각 센다.', '',
    '| 코호트 | 로드 세션 | hit(loaded related) | 미해결 related | graded micro | graded macro(분모 세션) | R / N / U | 채점 coverage | none 태스크 로드 |',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|');
  for (const [cohort, name] of [['codex', 'Codex 전체 라우터'], ['claude_v2', '기존 Claude V2']]) {
    for (const replicate of [...REPLICATES, 'pooled']) {
      const m = replicate === 'pooled' ? obs.metrics[cohort].pooled : obs.metrics[cohort].per_replicate[replicate];
      add(`| ${name} ${replicate === 'pooled' ? '합계' : replicate} | ${m.loaded_sessions}/${m.selected_sessions} | ${rate(m.hit_loaded_related)} | ${m.unresolved_loaded_related_sessions} | ${rate(m.precision_graded_micro)} | ${percent(m.precision_graded_macro.value)} (${m.precision_graded_macro.session_denominator}) | ${m.returned_ids.relevant} / ${m.returned_ids.graded_below_2} / ${m.returned_ids.ungraded} | ${rate(m.graded_coverage)} | ${rate(m.none_task_loading.loaded_among_all)} |`);
    }
  }
  add('', `Codex graded macro에서 채점된 반환이 하나도 없어 제외한 로드 세션: ${metrics.pooled.precision_graded_macro.excluded_loaded_sessions_without_grades}. 전체 반환 중 확인된 관련 스킬 비율: ${rate(metrics.pooled.confirmed_relevant_fraction_all_returned)}; U가 있으면 하한이다. 미채점 coverage: ${rate(metrics.pooled.unknown_coverage)}. path: ID ${metrics.pooled.returned_ids.path_ids}건은 다른 ID로 정규화하지 않았다.`, '',
    `기존 Claude V2 57개 세션은 ${link('기존 반환·원시 로그 참조', obs.sources.claude_v2.file)}에서 반환 ID와 요청 해시를 읽고, 이전 grade 값을 버린 뒤 같은 누적 4-0 oracle에 새로 결합했다. Claude를 다시 실행하지 않았다. 아래는 동일 태스크·동일 라벨로 계산한 관찰 비교이며, 호스트·모델·실행 시점이 다른 코호트의 차이를 라우터만의 인과 효과로 해석하지 않는다. 이전 Codex 보고서에 있던 재채점 전 수치를 복사하지 않았다.`, '',
    '| 코호트 합계 | 발화 | 검색 | 스킬 반환 | none 로드/검색된 none | none의 N / U | 실제 모델 기록 |', '|---|---:|---:|---:|---:|---:|---|');
  for (const [cohort, name] of [['codex', 'Codex'], ['claude_v2', 'Claude V2']]) {
    const m = obs.metrics[cohort].pooled;
    add(`| ${name} | ${ratio(m.skillfetch_called_sessions, m.selected_sessions)} | ${m.searched_sessions}/${m.selected_sessions} | ${m.loaded_sessions}/${m.selected_sessions} | ${rate(m.none_task_loading.loaded_among_searched)} | ${m.none_task_loading.graded_below_2_ids} / ${m.none_task_loading.ungraded_ids} | ${countText(m.model_session_counts)} |`);
  }
  add('', 'Claude의 비-load 호출에 대해 Codex와 같은 프로토콜 결과 증거가 없는 경우 0건의 성공으로 해석하지 않는다. 두 코호트의 로드 세트·관련성 지표만 같은 라벨 규칙으로 맞췄다.', '',
    '## 57개 주 세션 기록', '',
    '세션 링크는 원시 JSONL이다. 질의 링크는 원문을 재번역·축약하지 않은 별도 JSON이다. 종료 상태는 각 주 manifest.turn_id에 해당하는 lifecycle 결과이며, 코딩 품질 평가가 아니다. 원시 transcript에 함께 기록된 하위 turn 종료는 이 열에서 제외하고 별도 기록했다.', '',
    '| 세션 | 레포 | 호출 수 | 첫 도구 | 첫 호출 회차 | queries 원문·검사 | 반환 스킬 ID | 종료 / turn 상태 | 정리 |', '|---|---|---:|---|---|---|---|---|---|');
  for (const session of sessions) {
    const queries = session.search_calls.length ? session.search_calls.map(c => c.query_check_status).join(', ') : '미호출';
    const endings = primaryEndings(session);
    add(`| ${link(session.session_key, session.evidence.transcript)} | ${session.manifest.repo ?? '미확인'} | ${session.skillfetch_call_count} | ${session.first_call ? code(session.first_call.tool) : '없음'} | ${firstCycle(session.first_call)} | ${queryLink(session)}<br>${escaped(queries)} | ${returnedIds(session.loaded_skill_ids)} | ${code(session.result_status)} / ${escaped(endings)} | ${code(session.manifest.cleanup)} |`);
  }
  add('', '## 19개 태스크의 실제 선택 세트 비교', '',
    '각 칸은 실제 load 반환 ID의 세션 내 고유 집합이다. `[]`는 반환 없음, null은 증거 충돌·누락 등으로 확정할 수 없는 세트다. revision과 로컬 path를 그대로 표시한다.', '',
    '| 태스크 | Codex r1 | Codex r2 | Codex r3 | Claude V2 r1 | Claude V2 r2 | Claude V2 r3 |', '|---|---|---|---|---|---|---|');
  for (const row of obs.task_sets) add(`| ${row.task_id} | ${['codex', 'claude_v2'].flatMap(cohort => REPLICATES.map(r => returnedIds(row[cohort][r].loaded_skill_ids))).join(' | ')} |`);
  add('', '## 실패·부분 오류·미확인 기록', '',
    `실제 실행 종료 상태: ${countText(metrics.pooled.result_status_counts)}. 감사 판정은 별도 축이며 ${code(audit.status)}다. 실제 세션 실패를 증거 변조나 해시 불일치로 간주하지 않으며, 감사 FAIL도 전부 세션 실패 때문이라고 추정하지 않는다. 무결성 세부 판정: ${code(audit.integrity_status ?? (audit.status === 'PASS' ? 'PASS' : '별도 분류 없음; 실패 검사 참조'))}.`, '',
    `실패한 감사 검사: ${(audit.failed || []).map(code).join(', ') || '없음'}. 제출 관측이 없는 transcript ${audit.totals.missing_transcript_count}개는 0회 제출로 간주하지 않는다.`, '');
  add(`하위 에이전트 조사: ${link('57개 transcript SHA256와 전수 스캔 결과', evidence.childFile)}. 아래 seq는 링크된 원시 JSONL의 event_sequence와 행 번호다. 세 번의 실패는 ${code('no rollout found for thread id')} 오류이며 승인 거절로 분류하지 않았다.`, '',
    '| 주 세션 | spawn seq | task_name | fork_turns | 결과 | 출력 seq |', '|---|---:|---|---|---|---:|');
  for (const attempt of child.attempts) add(`| ${link(`${attempt.replicate}/${attempt.task_id}`, attempt.spawn.transcript_path)} | ${attempt.spawn.event_sequence} | ${code(attempt.arguments.task_name)} | ${attempt.arguments.fork_turns_explicit ? code(attempt.arguments.fork_turns) : '미지정'} | ${code(attempt.outcome)} | ${attempt.outputs.map(output => output.event_sequence).join(', ')} |`);
  add('', 'spawn message 인자는 모두 불투명한 gAAAA 접두 문자열이다. 위임 지시의 평문은 관측되지 않았으며 해독·재구성하지 않았다. 인자의 길이와 SHA256만 조사 JSON에 별도로 기록했다.', '');
  for (const finding of child.findings) {
    const lifecycle = finding.lifecycle.events.map(event => `${code(event.method)} seq ${event.event_sequence} (${code(event.status)})`).join(' → ');
    add(`${code(`${finding.replicate}/${finding.task_id}`)}의 실제 하위 에이전트 ${code(finding.child.agent_path)}, thread ${code(finding.child.thread_id)}: ${code(finding.child.model)} / ${code(finding.child.reasoning_effort)}는 subAgentActivity 메타데이터 관측값이다. ${lifecycle}; 하위 이벤트 ${finding.lifecycle.child_event_count}개, MCP 이벤트 ${finding.tool_usage.mcp_event_count}개. ${link('원시 기록', finding.transcript.path)}.`, '',
      `하위 도구 요청: ${countText(finding.tool_usage.raw_tool_counts)}. 명령 cwd는 주 worktree와 그 frontend 하위 디렉터리였고, 공유 worktree 제거·Git 등록 해제는 각각 ${code(finding.isolation_auth_cleanup.shared_worktree_removed)}, ${code(finding.isolation_auth_cleanup.shared_worktree_unregistered)}로 확인됐다. 하위 turn 종료는 ${code(finding.isolation_auth_cleanup.child_turn_completion)}지만 독립 하위 인증은 ${code(finding.isolation_auth_cleanup.independent_child_authentication)}, 독립 하위 프로세스 정리는 ${code(finding.isolation_auth_cleanup.independent_child_process_cleanup)}다. 별도 하위 worktree는 관측되지 않았다.`, '');
  }
  for (const session of sessions.filter(s => s.result_status !== 'COMPLETED')) add(`- 실행 종료 ${code(session.session_key)}: ${code(session.result_status)}; 제출=${session.prompt_submission.count}, 원문 일치=${session.prompt_submission.exact_frozen_prompt_match}, 정리=${code(session.manifest.cleanup)}. ${observationLink(session)}.`);
  const exceptionalLoads = loads.filter(c => c.protocol_status !== 'SUCCESS' || c.semantic_status !== 'SUCCESS' || c.return_conflict);
  const exceptionalCalls = calls.filter(c => c.protocol_status !== 'SUCCESS');
  add(`프로토콜 비성공 호출 ${exceptionalCalls.length}회, load 의미 상태 비성공·반환 충돌 ${exceptionalLoads.length}회. 실제 실패와 부분 오류는 아래와 원시 기록에 보존했다.`, '');
  for (const call of exceptionalCalls) add(`- ${call.session.session_key}, ${code(call.tool)}, ${code(call.id)}: protocol=${code(call.protocol_status)}, error=${code(JSON.stringify(call.error))}. ${observationLink(call.session)}.`);
  for (const call of exceptionalLoads) add(`- ${call.session.session_key}, load ${code(call.id)}: protocol=${code(call.protocol_status)}, semantic=${code(call.semantic_status)}, conflict=${call.return_conflict}, 반환=${returnedIds(call.returned_skill_ids)}. ${observationLink(call.session)}.`);
  if (!exceptionalCalls.length && !exceptionalLoads.length) add('관측된 MCP 프로토콜 오류와 load payload 오류·충돌은 없다.');
  const unknownSessions = sessions.filter(s => s.relevance_counts.ungraded > 0 || s.loaded === null);
  add('', `미채점 반환 또는 반환 세트 미확인 세션 ${unknownSessions.length}개: ${unknownSessions.map(s => `${code(s.session_key)} (U=${s.relevance_counts.ungraded}, ${code(s.hit_status)})`).join(', ') || '없음'}. 정확한 ID별 grade/null과 oracle 행 번호는 통합 관찰 JSON의 oracle_matches에 보존했다.`, '',
    `추출 경고 ${obs.warnings.length}건. ${link('전체 경고', evidence.observationFile)}의 warnings 배열을 참조한다.`, '',
    '## 적용 지침·설정·격리와 보존', '',
    `${link('실제로 배포한 전체 AGENTS.md', manifest.inputs.agents.snapshot_path)} · ${link('원본 라우터', path.join(__dirname, 'codex-e2e-3-preparation/router.original.SKILL.md'))} · ${link('Codex 호스트 수정 diff', path.join(__dirname, 'codex-e2e-3-preparation/router-codex.diff'))}. 원본의 When, 3–8단계, Rules를 보존했고, 1–2단계는 승인된 Codex 문구다. AGENTS SHA256 ${code(manifest.inputs.agents.sha256)}. 각 worktree에 복사한 직후와 turn/start 직전에 실제 바이트를 확인한 기록을 감사했다.`, '',
    `실제 config (${link('원본 파일', evidence.configFile)})는 MCP 승인 수정이 이미 적용된 E2E-2와 바이트가 같다. skillfetch 서버만 ${code('default_tools_approval_mode = "approve"')}이고, 전역 승인 정책·셸 sandbox·네트워크 제한은 아래와 같다.`, '',
    '```toml', evidence.config.trimEnd(), '```', '',
    `실제 CLI/model/reasoning과 account/read의 chatgpt/pro, login status, API 키 환경변수 미상속이 모두 확인된 주 세션은 ${evidence.identityVerified}/${sessions.length}개다. 나머지는 확인되지 않은 항목을 성공으로 세지 않는다. 각 주 세션의 실행 설정은 고정 s5의 새 detached worktree, 새 ephemeral thread, 격리된 HOME/CODEX_HOME을 사용한다. 등록 MCP는 skillfetch만이며 앱·플러그인·외부 스킬 자동 설치는 껐다. 셸 네트워크 차단은 MCP 서버 프로세스나 구독 추론 자체의 네트워크 금지로 해석하지 않는다. 하위 에이전트의 독립 인증·환경 격리는 이 주 세션 검사로 입증하지 않는다.`, '',
    `반복은 r1→r2→r3 순서이며 동시 실행 ${replicates[0].manifest.concurrency}개, 세션 제한 ${replicates[0].manifest.timeout_seconds}초, 모델 응답 회차 상한 ${replicates[0].manifest.assistant_round_cap === null ? '없음' : replicates[0].manifest.assistant_round_cap}이다. 관측된 prompt 제출 ${metrics.pooled.prompt_submission_checks.observed_turn_start_count}회 중 원문 일치 ${metrics.pooled.prompt_submission_checks.exact_matches}회, 불일치 ${metrics.pooled.prompt_submission_checks.mismatches}회다. UTC ${manifest.created_at} ~ ${manifest.finished_at}.`, '',
    `주 세션 정리 완료는 ${count(sessions, s => s.manifest.cleanup === 'DONE')}/57개다. worktree 디렉터리·Git 등록·인증 symlink 및 세 반복의 소유 임시 루트 제거를 감사했다. 이 결과를 하위 에이전트의 독립 프로세스·인증 정리 확인으로 확대하지 않는다. 원시 transcript, 종료 상태, 오류, 고정 소스·인덱스 지문은 보존했다.`, '',
    '| 고정 입력 | SHA256 또는 commit | 증거 |', '|---|---|---|');
  add(`| skillfetch 소스 | ${code(SOURCE_COMMIT)} | ${link('소스·인덱스 지문', manifest.inputs.source_preflight.snapshot_path)} |`);
  for (const [repo, commit] of Object.entries(replicates[0].manifest.repository_refs)) add(`| ${repo} s5 | ${code(commit)} | ${link('r1 manifest', replicates[0].source.manifest.file)} |`);
  for (const [key, input] of Object.entries(manifest.inputs)) add(`| ${key} | ${code(input.sha256)} | ${link('고정 입력', input.snapshot_path)} |`);
  add(`| oracle-4-0 | ${code(ORACLE_SHA)} | ${link('누적 oracle', obs.label_basis.oracle.file)} |`);
  for (const [name, file] of [['runtime audit (원래 FAIL 보존)', evidence.auditFile], ['하위 에이전트 조사', evidence.childFile], ['독립 지표 검증', evidence.independentFile]]) add(`| ${name} | ${code(sha(fs.readFileSync(file)))} | ${link('검증 증거', file)} |`);
  for (const report of evidence.oldReports) add(`| 이전 ${path.basename(report.file)} | ${code(report.sha256)} | ${link('변경하지 않은 보고서', report.file)} |`);
  add('', `소스 파일 ${Object.keys(sourcePreflight.source_files).length}개와 인덱스 파일 ${Object.keys(sourcePreflight.index_files).length}개의 개별 지문은 소스 preflight에 있다. 세션별 전후 검증과 현재 동일성은 감사 기록에 남겼다. 인덱스 파일 지문:`, '', '| 인덱스 파일 | SHA256 |', '|---|---|');
  for (const [name, hash] of Object.entries(sourcePreflight.index_files)) add(`| ${code(name)} | ${code(hash)} |`);
  add('', `보고서와 질의 JSON은 모델 호출 없이 종료된 기록에서 생성했다. 결과물 품질, 스킬 지침의 준수·유용성, 반복 간 차이의 통계적 유의성은 평가하지 않았다. 원시 로그를 별도로 읽은 지표 검증 ${code(evidence.independent.status)}는 런타임 감사 ${code(audit.status)}를 대체하지 않는다. 격리 요건 전체 통과나 스킬 선택의 정답을 보증하지 않는다.`, '',
    `${link('실행기', path.join(__dirname, 'codex-e2e-3-runner.cjs'))} · ${link('추출기', obs.sources.extractor.file)} · ${link('감사기', path.join(__dirname, 'codex-e2e-3-verify.cjs'))} · ${link('렌더러', __filename)}`, '');
  ensure(fullTasks.length === 57 && searches.length === metrics.pooled.query_checks_observed, 'Report observation count mismatch');
  return lines.join('\n');
}

function parseArgs(argv) {
  if (argv.length === 1 && ['--help', '-h'].includes(argv[0])) return { help: true };
  if (argv.length === 1 && argv[0] === '--self-test') return { selfTest: true };
  const options = { out: path.join(__dirname, 'codex-e2e-3.md'), check: false };
  const seen = new Set();
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    ensure(['--run-root', '--out', '--check'].includes(flag) && !seen.has(flag), `Unknown or repeated argument: ${flag}`);
    seen.add(flag);
    if (flag === '--check') options.check = true;
    else {
      ensure(argv[i + 1] && !argv[i + 1].startsWith('--'), `Missing value: ${flag}`);
      options[flag === '--run-root' ? 'runRoot' : 'out'] = path.resolve(argv[++i]);
    }
  }
  ensure(options.runRoot, HELP.trim());
  ensure(options.out.endsWith('.md'), 'Report output must be Markdown');
  return options;
}

function main(argv) {
  const options = parseArgs(argv);
  if (options.help) return process.stdout.write(HELP);
  if (options.selfTest) return selfTest();
  const evidence = loadEvidence(options.runRoot);
  const report = renderReport(evidence, options.out);
  const artifacts = queryArtifacts(evidence);
  const queryRoot = path.join(evidence.root, 'query-records');
  ensure(!fs.existsSync(options.out), `Refusing to overwrite report: ${options.out}`);
  ensure(!fs.existsSync(queryRoot), `Refusing to overwrite query evidence: ${queryRoot}`);
  ensure(fs.statSync(path.dirname(options.out)).isDirectory(), 'Report parent directory is missing');
  const summary = { mode: options.check ? 'CHECK_ONLY_NO_WRITES' : 'RENDERED', report: options.out, audit_status: evidence.audit.status,
    primary_sessions: evidence.sessions.length, child_threads: evidence.childFindings.child_thread_count, spawn_attempts: evidence.childFindings.spawn_agent_call_count,
    independent_metrics_status: evidence.independent.status, query_records: artifacts.length, report_bytes: Buffer.byteLength(report), report_sha256: sha(report) };
  if (!options.check) {
    fs.mkdirSync(queryRoot, { mode: 0o700 });
    for (const replicate of REPLICATES) fs.mkdirSync(path.join(queryRoot, replicate), { mode: 0o700 });
    for (const artifact of artifacts) fs.writeFileSync(artifact.file, `${JSON.stringify(artifact.value, null, 2)}\n`, { flag: 'wx', mode: 0o600 });
    fs.writeFileSync(options.out, report, { flag: 'wx', mode: 0o600 });
  }
  process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
}

function selfTest() {
  const evidence = {
    manifest: { status: 'COMPLETED', finished_at: '2026-10-24T00:00:00Z' },
    audit: { status: 'PASS', totals: { recorded_slots: 57, observed_turn_start_count: 57, missing_transcript_count: 0 } },
    replicates: ['r1', 'r2', 'r3'].map(id => ({ id, manifest: { status: 'COMPLETED', finished_at: '2026-10-24T00:00:00Z' } })),
    sessions: ['r1', 'r2', 'r3'].flatMap(replicate => Array.from({ length: 19 }, (_, i) => ({ replicate, task_id: `t${i}`, session_key: `${replicate}/t${i}` }))),
  };
  assert.throws(() => validateCompletion({ ...evidence, manifest: { status: 'RUNNING' } }), /terminal/);
  assert.throws(() => validateCompletion({ ...evidence, audit: { ...evidence.audit, status: 'RUNNING' } }), /audit/);
  assert.doesNotThrow(() => validateCompletion({ ...evidence, audit: { ...evidence.audit, status: 'FAIL' } }));
  assert.throws(() => validateCompletion({ ...evidence, sessions: evidence.sessions.slice(1) }), /57/);
  assert.doesNotThrow(() => validateCompletion(evidence));
  assert.match(firstCycle({ model_response_cycle: 2, model_response_cycle_mapping: 'unique_closed_code_exec_interval' }), /추론/);
  assert.match(firstCycle({ model_response_cycle: 2, model_response_cycle_mapping: 'direct_call_id' }), /직접/);
  assert.match(firstCycle(null), /미확인/);
  assert.match(returnedIds(null), /미확인/);
  assert.equal(returnedIds([]), '`[]`');
  assert.match(returnedIds(['org/skill@abc']), /org\/skill@abc/);
  assert.equal(primaryEndings({ manifest: { turn_id: 'primary' }, turn_end_events: [{ turn: { id: 'child', status: 'completed' } }, { turn: { id: 'primary', status: 'completed' } }] }), 'completed');
  assert.equal(primaryEndings({ manifest: { turn_id: 'primary' }, turn_end_events: [{ turn: { id: 'child', status: 'completed' } }] }), '미관측');
  assert.throws(() => parseArgs(['--run-root', '/tmp/run', '--check', '--check']), /repeated/);
  assert.equal(parseArgs(['--run-root', '/tmp/run', '--check']).check, true);
  assert.equal(parseArgs(['--help']).help, true);
  process.stdout.write('PASS: terminal/audit gates, preserved FAIL, cycle provenance, unknown/empty returns, CLI parsing; no files written\n');
}

module.exports = { validateCompletion, firstCycle, returnedIds, primaryEndings, loadEvidence, renderReport, queryArtifacts, parseArgs, main };
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
}
