#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { isDeepStrictEqual } = require('node:util');
const { validateCompletion, firstCycle, primaryEndings, returnedIds } = require('./codex-e2e-3-render.cjs');
const { readLabelBasis, joinLabels } = require('./codex-e2e-3-extract.cjs');
const REPLICATES = ['r1', 'r2', 'r3'];
const PREPARATION = path.join(__dirname, 'codex-e2e-4-preparation');
const DEFAULT_REPORT = path.join(__dirname, 'codex-e2e-4.md');
const SOURCE_COMMIT = '14d2020f1275e10a272eb46575c9bd6d4a2182e4';
const AGENTS_SHA = '00dcf1d460d2be692fb33b64a79d395ae567dbec9bbe44381978d877a53066b2';
const CONFIG_SHA = '69fb11307213035fce1442078304ff1891a1b4b22e5254a75d9387884bb590e1';
const ORACLE_SHA = '7db50e73c7dfd6b0b810ba65231fd1475a25a563651310592c88da23795e108c';
const HELP = 'Usage: node codex-e2e-4-render.cjs --run-root DIR [--out FILE.md] [--check]\nOffline only; requires terminal manifests and final hash-bound extraction/audit evidence.\nOnly the unchanged preparation/running-report.md snapshot may be replaced. Query records never overwrite.\n--check renders in memory without writing; --self-test runs offline unit checks.\n';
const ensure = (value, message) => { if (!value) throw new Error(message); };
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const count = (values, predicate) => values.filter(predicate).length;
const code = value => '`' + String(value ?? '미확인').replaceAll('`', '\\`').replaceAll('|', '\\|').replaceAll('\n', ' ') + '`';
const escaped = value => String(value).replaceAll('|', '\\|').replaceAll('\n', '<br>');
const percent = value => value == null ? 'N/A' : `${(value * 100).toFixed(1)}%`;
const ratio = (n, d) => `${n}/${d} (${d ? percent(n / d) : 'N/A'})`;
const rate = value => ratio(value.numerator, value.denominator);
const meanText = value => `${value.numerator}/${value.denominator}=${(value.value ?? value.observed_lower_bound_value)?.toFixed(3) ?? 'N/A'}${value.value === null ? ` (하한; 미확인 ${value.ambiguous_session_count}세션)` : ''}`;
const countText = values => Object.entries(values || {}).map(([key, value]) => `${code(key)} ${value}`).join(', ') || '없음';
const info = file => ({ file, sha256: sha(fs.readFileSync(file)) });

function assertHash(file, expected) {
  ensure(typeof expected === 'string' && sha(fs.readFileSync(file)) === expected, `Evidence changed: ${file}`);
}

function replacementAllowed(currentBytes, snapshotBytes, defaultTarget) {
  if (currentBytes === null) return 'CREATE';
  ensure(defaultTarget && currentBytes.equals(snapshotBytes), 'Refusing to replace a report that differs from the running-report snapshot');
  return 'REPLACE_RUNNING_SNAPSHOT';
}

function reportReplacement(target) {
  return replacementAllowed(fs.existsSync(target) ? fs.readFileSync(target) : null,
    fs.readFileSync(path.join(PREPARATION, 'running-report.md')), target === DEFAULT_REPORT);
}

function queryArtifacts(evidence) {
  const observationSha = sha(fs.readFileSync(evidence.observationFile));
  return evidence.sessions.map(session => {
    const length = evidence.observation.request_lengths.find(item => item.task_id === session.task_id);
    const prompt = evidence.prompts.get(session.task_id);
    ensure(typeof prompt === 'string' && sha(prompt) === length.prompt_sha256, `Frozen prompt mismatch: ${session.session_key}`);
    return { file: path.join(evidence.root, 'query-records', session.replicate, `${session.task_id}.json`), value: {
      schema_version: 1, session_key: session.session_key, source_observation_file: evidence.observationFile,
      source_observation_sha256: observationSha, replicate_observation_file: session.observation_file,
      replicate_observation_json_pointer: session.observation_json_pointer, transcript: session.evidence.transcript,
      original_frozen_prompt: prompt, prompt_length: length, prompt_submission: session.prompt_submission,
      search_calls: session.search_calls,
    } };
  });
}

function renderReport(evidence, target) {
  const { observation: obs, sessions, manifest, audit, root, replicates } = evidence;
  const link = (label, file) => `[${escaped(label)}](${path.relative(path.dirname(target), file).split(path.sep).map(encodeURIComponent).join('/')})`;
  const queryLink = session => link('원문 질의 JSON', path.join(root, 'query-records', session.replicate, `${session.task_id}.json`));
  const lines = [], add = (...values) => lines.push(...values);
  const metrics = obs.metrics.e2e4;
  const cohortName = { e2e4: 'E2E4 S-b′', e2e3: 'E2E3 S0' };
  add(`Codex CLI 0.164.0 | 모델: gpt-6-astra (reasoning: medium) | 인증: ChatGPT Pro (chatgpt/pro), API 키 환경변수 미상속 | 주 세션 실제 확인 ${evidence.identityVerified}/57`, '',
    '# Codex E2E 4: S-b′ 라우터, 19개 태스크 × 3회', '',
    `**주 세션 증거 감사 ${code(audit.status)}: ${audit.passed}/${audit.checked} 검사 통과. 하위 실행 없음 판정 ${code(audit.no_child_isolation_status)}.** 주 요청 제출 ${audit.totals.observed_turn_start_count ?? '미확인'}/57회, 주 세션 정상 종료 ${count(sessions, session => session.result_status === 'COMPLETED')}/57회. manifest=${code(manifest.status)}. 실제 하위·추가 thread ${evidence.childFindings.child_thread_count}개를 별도로 기록하며 주 세션 완료와 혼동하지 않는다. 실패·미확인 결과는 그대로 보존한다.`, '',
    `${link('종료 manifest', evidence.manifestFile)} · ${link('전수 감사', evidence.auditFile)} · ${link('통합 관찰·지표', evidence.observationFile)} · ${link('하위 에이전트 조사', evidence.childFile)}`, '',
    `주 지표는 **관련 태스크의 선택된 주 세션 전체에 대한 확인된 hit: ${rate(metrics.pooled.hit_all_related)}**다. 미로드도 분모에 포함한다. graded micro=${rate(metrics.pooled.precision_graded_micro)}, graded macro=${percent(metrics.pooled.precision_graded_macro.value)} (채점 가능한 ${metrics.pooled.precision_graded_macro.session_denominator}세션), 관련 스킬이 없는 태스크의 로드=${rate(metrics.pooled.none_task_loading.loaded_among_all)}다. 세션별 고유 반환 ID 수 평균은 ${meanText(metrics.pooled.mean_distinct_returned_ids_per_selected_session)}개다.`, '',
    '분모는 각각 관련 태스크 17×3=51개, 관련 스킬이 없는 태스크 2×3=6개, 전체 19×3=57개 주 세션이다. 하위 에이전트는 별도 태스크 표본으로 추가하지 않았다. 반환 ID 미확인(null)은 확인된 0개로 바꾸지 않는다. 미채점 또는 반환 증거 누락이 있으면 확인된 hit·확인된 반환 수는 하한이다.', '',
    `사용자가 지정한 ${link('S-b′ AGENTS.md 원본', evidence.preparation.agents_source)}을 수정 없이 적용했다. ${link('S0와의 실제 diff', path.join(PREPARATION, 'router-vs-s0.diff'))}에는 설명, 1–2단계, 검색 횟수 문구, 선택 기준, Rules 삭제 등 여러 차이가 있다. 따라서 E2E3와의 차이를 4단계 선택 문구 하나의 인과 효과로 해석하지 않는다. 코드 결과물의 품질은 채점하지 않았다.`, '',
    '## E2E3 S0와 동일 분모 비교', '',
    'R=grade≥2, N=grade<2, U=해당 태스크의 정확한 전체 ID에 기존 grade가 없는 반환이다. micro=ΣR/Σ(R+N), macro=채점된 ID가 있는 세션의 R/(R+N) 평균이다. U는 0점으로 간주하지 않고, macro 분모에서 제외한 세션 수를 별도로 기록한다. 고유 ID는 세션 안에서 중복 제거하며 서로 다른 세션에서는 각각 센다.', '',
    '| 코호트 | 확인된 hit / 전체 related | graded micro | graded macro(세션 수) | R / N / U | none 로드 / 전체 none | 고유 반환 평균 / 전체 세션 |',
    '|---|---:|---:|---:|---:|---:|---:|');
  for (const cohort of ['e2e4', 'e2e3']) for (const replicate of [...REPLICATES, 'pooled']) {
    const m = replicate === 'pooled' ? obs.metrics[cohort].pooled : obs.metrics[cohort].per_replicate[replicate];
    const mean = m.mean_distinct_returned_ids_per_selected_session;
    add(`| ${cohortName[cohort]} ${replicate === 'pooled' ? '합계' : replicate} | ${rate(m.hit_all_related)} | ${rate(m.precision_graded_micro)} | ${percent(m.precision_graded_macro.value)} (${m.precision_graded_macro.session_denominator}) | ${m.returned_ids.relevant} / ${m.returned_ids.graded_below_2} / ${m.returned_ids.ungraded} | ${rate(m.none_task_loading.loaded_among_all)} | ${meanText(mean)} |`);
  }
  add('', `E2E4의 확인된 반환 세트 미확인 ${metrics.pooled.ambiguous_return_sessions}세션, 미채점 반환이 있는 ${metrics.pooled.sessions_with_ungraded_returns}세션. graded macro에서 채점된 반환이 없어 제외한 로드 세션 ${metrics.pooled.precision_graded_macro.excluded_loaded_sessions_without_grades}개. 채점 coverage ${rate(metrics.pooled.graded_coverage)}, 미채점 coverage ${rate(metrics.pooled.unknown_coverage)}.`, '',
    `전체 related 분모 51개 안에서 확인된 미로드는 E2E4 ${metrics.pooled.hit_all_related_known_zero_load_sessions}개 / E2E3 ${obs.metrics.e2e3.pooled.hit_all_related_known_zero_load_sessions}개, 반환 증거·미채점으로 hit 여부가 미해결인 세션은 각각 ${metrics.pooled.hit_all_related_unresolved_sessions}개 / ${obs.metrics.e2e3.pooled.hit_all_related_unresolved_sessions}개다. 미해결 세션도 주 분모에서 제외하지 않는다.`, '',
    `보조 지표인 loaded-related hit는 E2E4 ${rate(metrics.pooled.hit_loaded_related)}, E2E3 ${rate(obs.metrics.e2e3.pooled.hit_loaded_related)}다. 이 값은 미로드를 분모에서 빼므로 위 주 지표와 구분한다. 기존 E2E3의 57개 원시 기록을 재사용하며 재실행·신규 grade 부여는 하지 않았다.`, '',
    `${link('누적 oracle-4-0', obs.label_basis.oracle.file)} SHA256=${code(obs.label_basis.oracle.sha256)}. 같은 누적 oracle에 전체 skill ID와 revision을 정확히 대조했다. 선택되지 않은 후보를 새로 채점하거나 path ID를 다른 ID로 치환하지 않았다.`, '',
    '## 호출·프로토콜·질의', '',
    '| 지표 | r1 | r2 | r3 | 합계 |', '|---|---:|---:|---:|---:|');
  const groups = [...REPLICATES.map(replicate => ({ sessions: sessions.filter(session => session.replicate === replicate), m: metrics.per_replicate[replicate] })), { sessions, m: metrics.pooled }];
  const row = (label, value) => add(`| ${label} | ${groups.map(value).join(' | ')} |`);
  row('주 요청 제출', group => `${group.m.prompt_submission_checks.observed_turn_start_count}/${group.sessions.length}`);
  row('skillfetch 호출 세션(발화율)', group => ratio(group.m.skillfetch_called_sessions, group.sessions.length));
  row('search 세션 / 호출 수', group => `${group.m.searched_sessions}/${group.sessions.length} · ${group.m.query_checks_observed}회`);
  row('queries 4개·4번째 원문 완전 일치', group => `${group.m.query_check_status_counts.PASS || 0}/${group.m.query_checks_observed}호출`);
  row('MCP 요청 / 결과 수신 / 프로토콜 성공', group => `${group.m.server_call_observations.total_calls} / ${group.m.server_call_observations.received_result} / ${group.m.server_call_observations.protocol_success}`);
  row('load 호출 / 실제 ID 반환 세션', group => `${group.m.load_call_count}회 / ${group.m.loaded_sessions}세션`);
  row('반환 없음 / 반환 미확인', group => `${group.m.not_loaded_sessions} / ${group.m.ambiguous_return_sessions}`);
  row('다른 thread / thread 미확인 MCP 호출', group => `${group.m.nonprimary_thread_mcp_call_count} / ${group.m.unscoped_mcp_call_count}`);
  row('주 turn 정상 종료 / 정리 DONE', group => `${count(group.sessions, session => session.result_status === 'COMPLETED')} / ${count(group.sessions, session => session.manifest.cleanup === 'DONE')}`);
  add('', `주 세션 도구별 호출: ${countText(metrics.pooled.skillfetch_tool_call_counts)}. 프로토콜 상태: ${countText(metrics.pooled.protocol_status_counts)}. load 의미 상태: ${countText(metrics.pooled.load_semantic_status_counts)}. 승인 거절 ${metrics.pooled.server_call_observations.approval_denied}회, 반환 충돌 ${metrics.pooled.load_return_conflicts}회. 서버 응답 수신·프로토콜 성공·실제 skills[].id 반환을 별도로 센다.`, '',
    `첫 skillfetch 호출 회차: ${countText(metrics.pooled.first_call_model_response_cycle.cycle_counts)}. 연결 방식: ${countText(metrics.pooled.first_call_model_response_cycle.mapping_counts)}. 미확인 ${metrics.pooled.first_call_model_response_cycle.unknown_sessions}개. 같은 주 thread/turn의 고유 rawResponse/completed.responseId 경계를 세며 exec 구간에 의한 연결은 추론으로 표시한다.`, '',
    '질의 검사는 모든 관측 인자에 대해 queries가 문자열 4개인지와 queries[3]가 고정 prompt에 완전히 일치하는지를 확인한다. 공백·줄바꿈·Unicode를 정규화하지 않았다. 별도 질의 JSON에 네 질의, 모든 lifecycle 인자, 원문 prompt와 해시를 보존한다.', '',
    `800자 이상은 Unicode code point 기준이며 해당 태스크 ${obs.long_request_task_ids.length}/19개, 반복 주 세션 ${obs.long_request_task_ids.length * 3}/57개다.`, '',
    '| 태스크 | 원문 문자 수 | 800자 이상 | r1 질의 | r2 질의 | r3 질의 |', '|---|---:|---|---|---|---|');
  for (const length of obs.request_lengths) add(`| ${length.task_id} | ${length.characters} | ${length.at_least_800 ? '예' : '아니오'} | ${REPLICATES.map(replicate => queryLink(sessions.find(session => session.task_id === length.task_id && session.replicate === replicate))).join(' | ')} |`);
  add('', '## 미로드와 none 판단 근거', '',
    '로드하지 않았다는 관찰만으로 “관련 스킬이 없어 의도적으로 생략했다”고 판단하지 않는다. 도구 미가용·승인/프로토콜 실패·빈 반환·명시적 선택 인자·모델 발언 근거를 분리하며, 아래 근거 JSON은 원시 발언과 이벤트 참조를 보존한다.', '');
  renderNoLoadEvidence(evidence, add, link);
  add('', '## 주 세션 57개 기록', '',
    '종료 열은 주 manifest.turn_id에 해당하는 종료만 센다. 첫 호출 회차의 “추론”은 도구와 모델 응답 경계의 연결 방식이다. 하위 thread와 도구 관찰은 주 세션 지표에서 분리한다.', '',
    '| 세션 | 첫 skillfetch 도구 / 회차 | 질의 원문 / q4 검사 | 실제 반환 ID | 종료 / 주 turn | 정리 | 하위 에이전트 |', '|---|---|---|---|---|---|---|');
  for (const session of sessions) add(`| ${link(session.session_key, session.evidence.transcript)} | ${session.first_call ? code(session.first_call.tool) : '없음'} / ${firstCycle(session.first_call)} | ${queryLink(session)}<br>${session.search_calls.map(call => call.query_check_status).join(', ') || '미호출'} | ${returnedIds(session.loaded_skill_ids)} | ${code(session.result_status)} / ${primaryEndings(session)} | ${code(session.manifest.cleanup)} | ${childSessionText(evidence, session)} |`);
  add('', '## 태스크별 실제 선택 세트', '',
    '반환 ID의 세션 내 고유 집합이다. []는 확인된 빈 집합, null은 반환 세트 미확인이다.', '',
    '| 태스크 | S-b′ r1 | S-b′ r2 | S-b′ r3 | S0 r1 | S0 r2 | S0 r3 |', '|---|---|---|---|---|---|---|');
  for (const task of obs.task_sets) add(`| ${task.task_id} | ${['e2e4', 'e2e3'].flatMap(cohort => REPLICATES.map(replicate => returnedIds(task[cohort][replicate].loaded_skill_ids))).join(' | ')} |`);
  add('', '## 실제 실패·하위 에이전트·한계', '',
    `주 세션 종료 상태: ${countText(metrics.pooled.result_status_counts)}. 실패한 감사 검사: ${(audit.failed || []).map(code).join(', ') || '없음'}. 추출 경고 ${obs.warnings.length}건은 통합 관찰 JSON에 보존했다.`, '');
  renderChildEvidence(evidence, add, link);
  for (const session of sessions.filter(item => item.result_status !== 'COMPLETED' || item.loaded === null || item.warnings.length)) add(`- ${code(session.session_key)}: 종료=${code(session.result_status)}, 로드=${code(session.loaded)}, hit=${code(session.hit_status)}, 정리=${code(session.manifest.cleanup)}. ${link('관찰 JSON', session.observation_file)} ${code(session.observation_json_pointer)}.`);
  const errors = sessions.flatMap(session => session.call_summaries.filter(call => call.protocol_status !== 'SUCCESS').map(call => ({ session, call })));
  for (const { session, call } of errors) add(`- MCP ${code(session.session_key)} ${code(call.tool)}: ${code(call.protocol_status)}, ${code(JSON.stringify(call.error))}. ${link('원시 기록', session.evidence.transcript)} seq ${call.event_sequence}.`);
  add('', '## 적용 원문·설정·보존', '',
    `${link('사용자가 지정한 AGENTS 원본', evidence.preparation.agents_source)} · ${link('실제 배포 snapshot', manifest.inputs.agents.snapshot_path)} · ${link('S0와의 diff', path.join(PREPARATION, 'router-vs-s0.diff'))}. 원본을 바이트 단위로 그대로 사용했다. SHA256=${code(AGENTS_SHA)}. 별도의 Codex 문구 수정은 하지 않았다.`, '',
    `${link('실제 config', evidence.configFile)}는 이전 실행과 같은 바이트다. skillfetch만 자동 승인하며 전역 approval_policy=never, sandbox=workspace-write, shell network=false를 유지한다.`, '',
    '```toml', evidence.config.trimEnd(), '```', '',
    `주 세션마다 s5의 새 detached worktree, 새 ephemeral thread, 격리 HOME/CODEX_HOME을 사용했다. 실제 CLI/model/effort와 chatgpt/pro 계정, API 키 환경변수 미상속 확인은 ${evidence.identityVerified}/57세션이다. 하위 에이전트의 독립 인증을 이 주 세션 증거로 대신하지 않는다. multi_agent=false·multi_agent_v2=false는 설정값이며 하위 실행 차단 보증이 아니다.`, '',
    `r1→r2→r3 순서, 동시 실행 ${replicates[0].manifest.concurrency ?? '미확인'}개, 제한 ${replicates[0].manifest.timeout_seconds ?? '미확인'}초. UTC ${manifest.created_at} ~ ${manifest.finished_at}. 정리 DONE ${count(sessions, session => session.manifest.cleanup === 'DONE')}/57개. worktree·Git 등록·인증 링크·소유 임시 디렉터리의 실제 제거 검사는 감사 기록에 있다.`, '',
    '| 고정 입력·증거 | SHA256 또는 commit | 링크 |', '|---|---|---|',
    `| skillfetch 소스 | ${code(SOURCE_COMMIT)} | ${link('소스·인덱스 지문', manifest.inputs.source_preflight.snapshot_path)} |`);
  for (const [name, input] of Object.entries(manifest.inputs)) add(`| ${name} | ${code(input.sha256)} | ${link('snapshot', input.snapshot_path)} |`);
  for (const [repo, commit] of Object.entries(replicates[0].manifest.repository_refs)) add(`| ${repo} s5 | ${code(commit)} | ${link('r1 manifest', replicates[0].source.manifest.file)} |`);
  for (const file of [...evidence.oldReports, info(evidence.auditFile), info(evidence.childFile), info(evidence.observationFile), ...(evidence.noneReview ? [info(evidence.noneReviewFile)] : []), info(path.join(PREPARATION, 'running-report.md')), info(path.join(PREPARATION, 'waiting-report.md'))]) add(`| ${path.basename(file.file)} | ${code(file.sha256)} | ${link('보존 증거', file.file)} |`);
  add('', `소스 ${Object.keys(evidence.sourcePreflight.source_files).length}개·인덱스 ${Object.keys(evidence.sourcePreflight.index_files).length}개의 파일별 지문은 source-preflight에 있다. 이전 E2E2·E2E3 보고서를 수정하지 않았다. 실행 중 보고서는 preparation/running-report.md와 바이트가 같을 때만 이 최종 보고서로 교체하며 기존 대기 보고서도 보존했다.`, '',
    '보고서·질의 JSON 생성에는 모델 호출을 사용하지 않았다. 결과물 품질·스킬 준수·통계적 유의성은 평가하지 않았다. 주 세션 완료, 지표 재계산, 런타임 격리 감사는 각각 별도 판정이다.', '',
    `${link('실행기', path.join(__dirname, 'codex-e2e-4-runner.cjs'))} · ${link('추출기', path.join(__dirname, 'codex-e2e-4-extract.cjs'))} · ${link('감사기', path.join(__dirname, 'codex-e2e-4-verify.cjs'))} · ${link('렌더러', __filename)}`, '');
  return lines.join('\n');
}

function renderNoLoadEvidence(evidence, add, link) {
  const reviewed = evidence.noneReview?.sessions || [];
  const verdictCounts = reviewed.reduce((out, item) => ({ ...out, [item.verdict]: (out[item.verdict] || 0) + 1 }), {});
  add(evidence.noneReview ? `${link('수동 검토 근거', evidence.noneReviewFile)}: ${countText(verdictCounts)}. 검토 결과를 관측 JSON 해시와 주 세션 원시 발언에 대조했다.` : '수동 none 판단 검토 파일이 없어 모든 미로드의 의도는 미검토로 남겼다.', '',
    '| 세션 | oracle related | 실제 반환 | 관측 분류 | 도구 실패 / 의미 오류 / 빈 load / 빈 auto 선택 | 수동 판단 | 근거 |', '|---|---|---|---|---|---|---|');
  for (const session of evidence.sessions.filter(item => !item.oracle_related || item.loaded !== true)) {
    const observation = session.no_load_evidence;
    const review = reviewed.find(item => item.session_key === session.session_key);
    const pointers = review?.evidence.map(item => `seq ${item.event_sequence}, L${item.transcript_line}`).join('; ');
    add(`| ${link(session.session_key, session.evidence.transcript)} | ${session.oracle_related ? '예' : '없음'} | ${returnedIds(session.loaded_skill_ids)} | ${code(observation.status)} | ${observation.tool_failures.length} / ${observation.semantic_errors.length} / ${observation.successful_empty_loads.length} / ${observation.empty_resolve_selection_arguments.length} | ${review ? code(review.verdict) : session.loaded === true ? '반환됨' : '미검토'} | ${review ? `${escaped(review.reason)}<br>${pointers || '명시 발언 없음'}` : `${observation.decision_excerpts.length}개 발언 후보; 의도 미확정`} |`);
  }
  add('', `모든 발언 후보·선택 인자·도구 실패는 ${link('통합 관찰 JSON', evidence.observationFile)}의 각 세션 no_load_evidence에 있다. 빈 auto_ids만으로 pinned_ids까지 비었거나 명시적으로 none을 선택했다고 추정하지 않는다. 미로드 원인과 oracle의 관련 스킬 유무는 다른 축이다.`);
}
function childSessionText(evidence, session) {
  const scan = evidence.childFindings.scans.find(item => item.replicate === session.replicate && item.task_id === session.task_id);
  if (!scan || scan.scan_status !== 'PASS') return '미확인';
  const findings = evidence.childFindings.findings.filter(item => item.replicate === session.replicate && item.task_id === session.task_id);
  return `시도 ${scan.spawn_agent_call_count}, 실행 ${scan.observed_child_thread_ids.length}, 메타데이터만 ${count(findings, item => !item.execution_observed)}`;
}

function renderChildEvidence(evidence, add, link) {
  const child = evidence.childFindings;
  add(`${link('하위 에이전트 전수 조사', evidence.childFile)}: 검사 가능 ${child.primary_sessions_scanned}/57개, spawn 시도 ${child.spawn_agent_call_count}회, 실행 관측 ${child.child_thread_count}thread(모델 spawn과 연결된 thread ${child.model_created_child_thread_count}개), 메타데이터만 관측 ${child.metadata_only_thread_count}개. 고유 관측 runtime thread/turn ${child.unique_observed_runtime_threads}/${child.unique_observed_runtime_turns}개, 하위 MCP lifecycle 이벤트 ${child.child_mcp_event_count}개.`, '',
    `하위 실행 없음 판정=${code(child.no_child_isolation_status)}은 주 세션 감사=${code(evidence.audit.status)}와 별개다. 로그에 하위 실행이 없더라도 설정이 이를 차단한다는 보증은 아니다. 주 세션의 MCP·검색·로드·관련성 지표는 manifest.thread_id에 속하는 호출만 집계한다.`, '');
  if (child.attempts.length) {
    add('| 주 세션 | spawn seq | task_name / fork_turns | 실제 결과 | 출력 seq |', '|---|---:|---|---|---:|');
    for (const attempt of child.attempts) add(`| ${link(`${attempt.replicate}/${attempt.task_id}`, attempt.spawn.transcript_path)} | ${attempt.spawn.event_sequence} | ${code(attempt.arguments.task_name)} / ${attempt.arguments.fork_turns_explicit ? code(attempt.arguments.fork_turns) : '미지정'} | ${code(attempt.outcome)} | ${attempt.outputs.map(output => output.event_sequence).join(', ') || '미관측'} |`);
    add('', 'spawn 실패의 원문·종류는 조사 JSON의 outputs에 보존했다. 승인 거절인지, 문맥 누락인지, 다른 오류인지 원시 결과에 따라 구분한다. 불투명한 위임 message의 평문을 추정하지 않는다.', '');
  }
  for (const finding of child.findings) add(`- ${code(`${finding.replicate}/${finding.task_id}`)} ${code(finding.child.agent_path)}, thread=${code(finding.child.thread_id)}, 분류=${code(finding.source_classification)}, 실행 관측=${finding.execution_observed}. 모델/effort=${code(finding.child.model)}/${code(finding.child.reasoning_effort)}는 activity 메타데이터다. lifecycle: ${finding.lifecycle.events.map(event => `${code(event.method)} seq${event.event_sequence} ${code(event.status)}`).join('; ') || '미관측'}. 하위 MCP 이벤트 ${finding.tool_usage.mcp_event_count}개. 하위 turn 완료=${code(finding.isolation_auth_cleanup.child_turn_completion)}. 독립 인증·프로세스 정리는 ${code('NOT_VERIFIED')}이며 주 세션 정리로 대체하지 않는다. ${link('원시 기록', finding.transcript.path)}.`);
  add('', `E2E3 기준 실행은 원래 감사 ${code(evidence.baselineAudit.status)}를 보존한다. ${link('E2E3 원래 감사', evidence.baselineAuditFile)} · ${link('E2E3 하위 에이전트 조사', evidence.baselineChildFile)}. 당시 주 세션 57개 외 실제 하위 thread ${evidence.baselineChild.child_thread_count}개가 있었으며, 이번 비교에서 해당 주 세션을 제외하거나 다시 실행하지 않았다. 두 감사의 primary/child 분리 규칙 차이도 있으므로 PASS/FAIL 문자열 자체를 개선 효과로 비교하지 않는다.`);
}

function loadNoneReview(file, observationFile, sessions) {
  if (!fs.existsSync(file)) return null;
  const review = read(file);
  ensure(review.schema_version === 1 && review.observations_sha256 === sha(fs.readFileSync(observationFile)), 'None-decision review is stale or malformed');
  const candidates = sessions.filter(session => session.loaded !== true);
  ensure(review.sessions.length === candidates.length && new Set(review.sessions.map(item => item.session_key)).size === candidates.length, 'None-decision review must cover every non-loaded or unresolved session exactly once');
  for (const item of review.sessions) {
    const session = candidates.find(candidate => candidate.session_key === item.session_key);
    ensure(session && ['EXPLICIT_NONE', 'NO_LOAD_UNRESOLVED', 'EMPTY_AUTO_SELECTION', 'TOOL_FAILURE'].includes(item.verdict) && typeof item.reason === 'string' && Array.isArray(item.evidence), `Invalid none-decision review: ${item.session_key}`);
    const transcript = fs.readFileSync(session.evidence.transcript, 'utf8').split('\n');
    for (const citation of item.evidence) {
      ensure(Number.isInteger(citation.transcript_line) && citation.transcript_line > 0 && typeof citation.quote === 'string' && citation.quote.length > 0, 'Invalid review citation');
      const event = JSON.parse(transcript[citation.transcript_line - 1]);
      const params = event.message?.params;
      ensure(event.sequence === citation.event_sequence && params?.threadId === session.manifest.thread_id && params?.turnId === session.manifest.turn_id && params?.item?.type === 'agentMessage' && params.item.text.includes(citation.quote), `None-decision quote is not an exact primary assistant message: ${item.session_key}`);
    }
    ensure(item.verdict !== 'EXPLICIT_NONE' || item.evidence.length > 0, 'EXPLICIT_NONE needs exact assistant evidence');
    ensure(item.verdict !== 'EMPTY_AUTO_SELECTION' || session.no_load_evidence.empty_resolve_selection_arguments.length > 0, 'EMPTY_AUTO_SELECTION needs observed arguments');
    ensure(item.verdict !== 'TOOL_FAILURE' || session.no_load_evidence.tool_failures.length > 0 || item.evidence.length > 0, 'TOOL_FAILURE needs protocol or quoted availability evidence');
  }
  return review;
}

function validateSourceDescriptors(value) {
  if (!value || typeof value !== 'object') return;
  if (typeof value.file === 'string' && typeof value.sha256 === 'string') assertHash(value.file, value.sha256);
  if (typeof value.observations_file === 'string' && typeof value.observations_sha256 === 'string') assertHash(value.observations_file, value.observations_sha256);
  for (const child of Object.values(value)) if (child && typeof child === 'object') validateSourceDescriptors(child);
}

function loadEvidence(runRoot) {
  const root = fs.realpathSync(runRoot), manifestFile = path.join(root, 'manifest.json');
  const manifest = read(manifestFile);
  ensure(['COMPLETED', 'COMPLETED_WITH_FAILURES', 'FAILED', 'INTERRUPTED'].includes(manifest.status) && manifest.finished_at, 'Root manifest is not terminal');
  const auditFile = path.join(root, 'audit-verification.json'), observationFile = path.join(root, 'observations-e2e4.json');
  const audit = read(auditFile), observation = read(observationFile);
  ensure(observation.schema_version === 4 && observation.run_root === root && audit.run_root === root, 'Wrong observation/audit schema or run root');
  assertHash(manifestFile, audit.manifest_sha256);
  assertHash(path.join(__dirname, 'codex-e2e-4-verify.cjs'), audit.auditor_sha256);
  validateSourceDescriptors(observation.sources);
  const replicates = REPLICATES.map(id => {
    const source = observation.sources.runs.find(item => item.replicate === id);
    ensure(source?.run_directory === path.join(root, id), `Wrong replicate source: ${id}`);
    const measured = read(source.observations_file), replicateManifest = read(source.manifest.file);
    ensure(measured.source_evidence_kind === 'MEASURED_MODEL_RUN' || measured.source_evidence_kind === null, 'Synthetic evidence cannot produce a measured report');
    ensure(replicateManifest.source_commit === SOURCE_COMMIT && replicateManifest.agents_sha256 === AGENTS_SHA, `Wrong source or AGENTS pin: ${id}`);
    ensure(audit.replicates.find(item => item.id === id)?.manifest_sha256 === source.manifest.sha256, `Wrong audited manifest: ${id}`);
    return { id, source, measured, manifest: replicateManifest };
  });
  const sessions = observation.sessions.e2e4;
  validateCompletion({ manifest, audit, replicates, sessions });
  ensure(observation.sessions.e2e3.length === 57 && observation.task_sets.length === 19 && observation.request_lengths.length === 19, 'Incomplete current/baseline task matrix');
  ensure(observation.label_basis.oracle.sha256 === ORACLE_SHA && observation.label_basis.related_task_count === 17 && observation.label_basis.no_related_task_count === 2, 'Wrong oracle or task split');
  assertHash(observation.label_basis.oracle.file, ORACLE_SHA);
  assertHash(observation.label_basis.basis.file, observation.label_basis.basis.sha256);
  const labels = readLabelBasis(observation.label_basis.basis.file);
  const { aggregateMetrics } = require('./codex-e2e-4-extract.cjs');
  for (const cohort of ['e2e4', 'e2e3']) {
    const selected = observation.sessions[cohort];
    ensure(new Set(selected.map(session => session.session_key)).size === 57, `Duplicate cohort sessions: ${cohort}`);
    for (const session of selected) for (const [key, expected] of Object.entries(joinLabels(session.task_id, session.loaded_skill_ids, labels.rows))) ensure(isDeepStrictEqual(session[key], expected), `Oracle join differs: ${cohort}/${session.session_key}/${key}`);
    ensure(isDeepStrictEqual(aggregateMetrics(selected), observation.metrics[cohort].pooled), `Pooled metrics differ: ${cohort}`);
    for (const replicate of REPLICATES) {
      const subset = selected.filter(session => session.replicate === replicate);
      ensure(subset.length === 19 && isDeepStrictEqual(aggregateMetrics(subset), observation.metrics[cohort].per_replicate[replicate]), `Replicate metrics differ: ${cohort}/${replicate}`);
    }
    ensure(observation.metrics[cohort].pooled.hit_all_related.denominator === 51 && observation.metrics[cohort].pooled.mean_distinct_returned_ids_per_selected_session.denominator === 57 && observation.metrics[cohort].pooled.none_task_loading.loaded_among_all.denominator === 6, `Primary denominator changed: ${cohort}`);
  }
  for (const session of sessions) {
    const audited = audit.tasks.find(item => item.replicate === session.replicate && item.id === session.task_id);
    ensure(audited, `Missing audited session: ${session.session_key}`);
    if (audited.transcript_sha256) assertHash(session.evidence.transcript, audited.transcript_sha256);
    const task = replicates.find(item => item.id === session.replicate).measured.tasks.find(item => item.id === session.task_id);
    ensure(task && isDeepStrictEqual(session.manifest, task.manifest) && isDeepStrictEqual(session.loaded_skill_ids, task.returned_skill_ids) && isDeepStrictEqual(session.search_calls, task.search_calls) && isDeepStrictEqual(session.load_calls, task.load_calls) && isDeepStrictEqual(session.no_load_evidence, task.no_load_evidence), `Session differs from per-run source: ${session.session_key}`);
    ensure(session.call_summaries.every(call => call.thread_id === session.manifest.thread_id) && session.call_summaries.length === task.calls.length, `Wrong primary MCP scope: ${session.session_key}`);
    for (const [key, expected] of Object.entries({ cli_version: '0.164.0', model: 'gpt-6-astra', reasoning_effort: 'medium', auth_mode: 'chatgpt', auth_plan_type: 'pro' })) ensure(session.manifest[key] == null || session.manifest[key] === expected, `Unexpected identity: ${session.session_key}/${key}`);
  }
  for (const input of Object.values(manifest.inputs)) assertHash(input.snapshot_path, input.sha256);
  const preparation = read(path.join(PREPARATION, 'preparation.json'));
  ensure(audit.preparation.path === path.join(PREPARATION, 'preparation.json'), 'Audit preparation source differs');
  assertHash(audit.preparation.path, audit.preparation.sha256);
  ensure(preparation.agents_modified === false && preparation.agents_sha256 === AGENTS_SHA && manifest.inputs.agents.sha256 === AGENTS_SHA && preparation.source_commit === SOURCE_COMMIT, 'Wrong unchanged S-b-prime source');
  assertHash(preparation.agents_source, AGENTS_SHA);
  assertHash(path.join(PREPARATION, 'AGENTS.md'), AGENTS_SHA);
  const configFile = manifest.inputs.config.snapshot_path;
  assertHash(configFile, CONFIG_SHA);
  assertHash(path.join(__dirname, 'codex-e2e-3-preparation/config-template.toml'), CONFIG_SHA);
  const config = fs.readFileSync(configFile, 'utf8');
  const sourcePreflight = read(manifest.inputs.source_preflight.snapshot_path);
  ensure(sourcePreflight.status === 'PASS' && sourcePreflight.source_commit === SOURCE_COMMIT, 'Source preflight mismatch');
  const oldReports = Object.entries(preparation.old_report_hashes).map(([name, expected]) => { const file = path.join(__dirname, name); assertHash(file, expected); return { file, sha256: expected }; });
  const prompts = new Map(fs.readFileSync(manifest.inputs.tasks.snapshot_path, 'utf8').trimEnd().split('\n').map(line => { const task = JSON.parse(line); return [task.id, task.prompt]; }));
  ensure(prompts.size === 19, 'Wrong frozen prompt count');
  for (const session of sessions) ensure(/^[A-Za-z0-9_-]+$/.test(session.task_id) && prompts.has(session.task_id) && session.session_key === `${session.replicate}/${session.task_id}`, 'Unsafe or wrong query output path');
  const identityVerified = count(sessions, session => {
    const task = session.manifest, flags = task.login_status?.api_key_environment_absent;
    return task.cli_version === '0.164.0' && task.model === 'gpt-6-astra' && task.reasoning_effort === 'medium' && task.auth_mode === 'chatgpt' && task.auth_plan_type === 'pro' && task.login_status?.chatgpt === true && flags && Object.keys(flags).length >= 8 && Object.values(flags).every(value => value === true);
  });
  const noneReviewFile = path.join(root, 'none-decision-review.json'), noneReview = loadNoneReview(noneReviewFile, observationFile, sessions);
  const childEvidence = loadChildEvidence(root, auditFile, audit, sessions);
  const baselineRoot = path.dirname(observation.sources.e2e3.file);
  const baselineAuditFile = path.join(baselineRoot, 'audit-verification.json'), baselineChildFile = path.join(baselineRoot, 'child-agent-findings.json');
  const baselineAudit = read(baselineAuditFile), baselineChild = read(baselineChildFile);
  assertHash(baselineAuditFile, baselineChild.audit.sha256);
  assertHash(path.join(baselineRoot, 'manifest.json'), baselineAudit.manifest_sha256);
  ensure(audit.baseline.run_root === baselineRoot && audit.baseline.manifest_sha256 === baselineAudit.manifest_sha256, 'Wrong audited S0 baseline');
  return { root, manifestFile, manifest, auditFile, audit, observationFile, observation, sessions, replicates, preparation, configFile, config, sourcePreflight, oldReports, prompts, identityVerified, noneReviewFile, noneReview, baselineAuditFile, baselineAudit, baselineChildFile, baselineChild, ...childEvidence };
}

function loadChildEvidence(root, auditFile, audit, sessions) {
  const childFile = path.join(root, 'child-agent-findings.json'), childFindings = read(childFile);
  ensure(childFindings.schema_version === 1 && childFindings.run_root === root && childFindings.audit_file === auditFile && childFindings.audit.path === auditFile && childFindings.audit.status === audit.status && childFindings.audit.checked === audit.checked && childFindings.audit.passed === audit.passed, 'Child evidence audit binding differs');
  assertHash(auditFile, childFindings.audit_sha256);
  ensure(childFindings.audit.sha256 === childFindings.audit_sha256 && childFindings.auditor_sha256 === audit.auditor_sha256 && childFindings.manifest_sha256 === audit.manifest_sha256 && childFindings.no_child_isolation_status === audit.no_child_isolation_status, 'Child evidence audit hashes or isolation result differ');
  ensure(childFindings.scans.length === 57 && new Set(childFindings.scans.map(item => `${item.replicate}/${item.task_id}`)).size === 57 && childFindings.primary_sessions_scanned === count(childFindings.scans, item => item.scan_status === 'PASS'), 'Incomplete child scan slots');
  for (const scan of childFindings.scans) {
    const session = sessions.find(item => item.session_key === `${scan.replicate}/${scan.task_id}`);
    ensure(session, 'Unexpected child scan session');
    if (scan.scan_status === 'PASS') {
      assertHash(session.evidence.transcript, scan.transcript_sha256);
      ensure(scan.primary_thread_id === session.manifest.thread_id && scan.primary_turn_id === session.manifest.turn_id && scan.controller_turn_start_count === session.prompt_submission.count, 'Child scan primary scope differs');
    }
  }
  const observed = childFindings.findings.filter(item => item.execution_observed);
  ensure(childFindings.attempts.length === childFindings.spawn_agent_call_count && childFindings.child_thread_count === new Set(observed.map(item => item.child.thread_id)).size && childFindings.child_mcp_event_count === childFindings.findings.reduce((total, item) => total + item.tool_usage.mcp_event_count, 0), 'Child counts differ');
  for (const finding of childFindings.findings) assertHash(finding.transcript.path, finding.transcript.sha256);
  ensure(!observed.length || childFindings.no_child_isolation_status === 'FAIL', 'Observed child execution cannot claim no-child PASS');
  return { childFile, childFindings };
}

function parseArgs(argv) {
  if (argv.length === 1 && ['--help', '-h'].includes(argv[0])) return { help: true };
  if (argv.length === 1 && argv[0] === '--self-test') return { selfTest: true };
  const options = { out: DEFAULT_REPORT, check: false }, seen = new Set();
  for (let index = 0; index < argv.length; index++) {
    const flag = argv[index];
    ensure(['--run-root', '--out', '--check'].includes(flag) && !seen.has(flag), `Unknown or repeated argument: ${flag}`);
    seen.add(flag);
    if (flag === '--check') options.check = true;
    else { ensure(argv[index + 1] && !argv[index + 1].startsWith('--'), `Missing value: ${flag}`); options[flag === '--run-root' ? 'runRoot' : 'out'] = path.resolve(argv[++index]); }
  }
  ensure(options.runRoot, HELP.trim());
  ensure(options.out.endsWith('.md'), 'Output must be Markdown');
  return options;
}

function main(argv) {
  const options = parseArgs(argv);
  if (options.help) return process.stdout.write(HELP);
  if (options.selfTest) return selfTest();
  const evidence = loadEvidence(options.runRoot);
  const report = renderReport(evidence, options.out);
  const artifacts = queryArtifacts(evidence), queryRoot = path.join(evidence.root, 'query-records');
  const replacement = reportReplacement(options.out);
  ensure(!fs.existsSync(queryRoot), `Refusing to overwrite query records: ${queryRoot}`);
  ensure(fs.statSync(path.dirname(options.out)).isDirectory(), 'Report parent directory does not exist');
  if (!options.check) {
    fs.mkdirSync(queryRoot, { mode: 0o700 });
    for (const replicate of REPLICATES) fs.mkdirSync(path.join(queryRoot, replicate), { mode: 0o700 });
    for (const artifact of artifacts) fs.writeFileSync(artifact.file, JSON.stringify(artifact.value, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
    ensure(reportReplacement(options.out) === replacement, 'Report changed before final replacement');
    fs.writeFileSync(options.out, report, { flag: replacement === 'CREATE' ? 'wx' : 'w', mode: 0o600 });
  }
  process.stdout.write(JSON.stringify({ mode: options.check ? 'CHECK_ONLY_NO_WRITES' : 'RENDERED', report: options.out, replacement, audit_status: evidence.audit.status,
    primary_sessions: evidence.sessions.length, query_records: artifacts.length, report_bytes: Buffer.byteLength(report), report_sha256: sha(report) }, null, 2) + '\n');
}

function selfTest() {
  assert.equal(replacementAllowed(null, Buffer.from('running'), true), 'CREATE');
  assert.equal(replacementAllowed(Buffer.from('running'), Buffer.from('running'), true), 'REPLACE_RUNNING_SNAPSHOT');
  assert.throws(() => replacementAllowed(Buffer.from('final'), Buffer.from('running'), true), /Refusing/);
  assert.throws(() => replacementAllowed(Buffer.from('running'), Buffer.from('running'), false), /Refusing/);
  assert.equal(primaryEndings({ manifest: { turn_id: 'primary' }, turn_end_events: [{ turn: { id: 'child', status: 'completed' } }, { turn: { id: 'primary', status: 'completed' } }] }), 'completed');
  assert.match(returnedIds(null), /미확인/);
  assert.equal(returnedIds([]), '`[]`');
  assert.throws(() => parseArgs(['--run-root', '/tmp/run', '--check', '--check']), /repeated/);
  assert.equal(parseArgs(['--run-root', '/tmp/run', '--check']).check, true);
  const { aggregateMetrics } = require('./codex-e2e-4-extract.cjs');
  const labels = new Map([
    ['related', { line: 1, row: { pool: [{ skill: 'skill@r1', grade: 2 }] } }],
    ['none', { line: 2, row: { pool: [{ skill: 'other@r1', grade: 0 }] } }],
  ]);
  const session = (task, ids) => ({ cohort: 'codex', search_calls: [], load_calls: [], call_summaries: [], ...joinLabels(task, ids, labels) });
  const metrics = aggregateMetrics([session('related', ['skill@r1']), session('related', []), session('none', [])]);
  assert.equal(metrics.hit_all_related.numerator, 1);
  assert.equal(metrics.hit_all_related.denominator, 2);
  assert.equal(metrics.hit_loaded_related.denominator, 1);
  assert.equal(metrics.mean_distinct_returned_ids_per_selected_session.denominator, 3);
  assert.equal(metrics.mean_distinct_returned_ids_per_selected_session.value, 1 / 3);
  const uncertain = aggregateMetrics([session('related', ['skill@r1']), session('related', null), session('none', [])]);
  assert.equal(uncertain.hit_all_related.denominator, 2);
  assert.equal(uncertain.mean_distinct_returned_ids_per_selected_session.value, null);
  assert.match(meanText(uncertain.mean_distinct_returned_ids_per_selected_session), /하한/);
  process.stdout.write('PASS: all-related denominator includes no-load, mean includes zero, unknown stays unknown, exact interim replacement, primary endings, CLI; no files written\n');
}

module.exports = { replacementAllowed, reportReplacement, queryArtifacts, renderReport, loadEvidence, loadNoneReview, loadChildEvidence, parseArgs, main };
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { process.stderr.write(error.message + '\n'); process.exitCode = 1; }
}
