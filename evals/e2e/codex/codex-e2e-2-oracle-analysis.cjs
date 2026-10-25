'use strict';
// Offline analysis of saved recordings only. No child processes or network calls.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const base = __dirname;
const run = path.join(base, 'codex-e2e-runs/20261024-subscription-mcp-approved-14d2020');
const reportPath = path.join(base, 'codex-e2e-2.md');
const artifactPath = path.join(base, 'codex-e2e-2-oracle-analysis.json');
const marker = '## 후속 분석: oracle 관련성 및 Claude Code Stage 5 V2 비교';
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const readJsonl = file => fs.readFileSync(file, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
const taskPath = path.join(base, 'stage5/tasks.jsonl');
const oraclePath = path.join(base, 'stage5/oracle.jsonl');
const observationsPath = path.join(run, 'observations.json');
const v2Path = path.join(base, 'codex-e2e-2-oracle-v2.json');
const tasks = readJsonl(taskPath);
const oracleRows = readJsonl(oraclePath);
const observations = readJson(observationsPath);
const v2 = readJson(v2Path);
const before = fs.readFileSync(reportPath);
assert.equal(sha(before), 'd5b8d8ca79f8be1e4963532eb98d16a94c60b46ee018d64010507f28735113c3');
assert(!before.toString('utf8').includes(marker), 'Appendix already exists');
assert(!fs.existsSync(artifactPath), 'Analysis artifact already exists');
assert(fs.readFileSync(taskPath).equals(fs.readFileSync(path.join(run, 'tasks.jsonl'))));
assert.equal(tasks.length, 19);
assert.equal(new Set(tasks.map(t => t.id)).size, 19);
assert.equal(oracleRows.length, 19);
assert.equal(v2.sessions.length, 57);
const oracle = new Map();
for (const row of oracleRows) {
  assert(!oracle.has(row.id));
  const grades = new Map();
  for (const entry of row.pool) {
    assert(Number.isInteger(entry.grade) && entry.grade >= 0 && entry.grade <= 3);
    if (grades.has(entry.skill)) assert.equal(grades.get(entry.skill), entry.grade);
    grades.set(entry.skill, entry.grade);
  }
  const relevant = [...grades].filter(([,grade]) => grade >= 2).map(([id]) => id).sort();
  assert.deepEqual(Object.keys(row.relevant_grades || {}).sort(), relevant);
  for (const [id, grade] of Object.entries(row.relevant_grades || {})) assert.equal(grades.get(id), grade);
  oracle.set(row.id, {grades, relevant, expect_none:row.expect_none});
}
function classify(taskId, ids, extra = {}) {
  assert(Array.isArray(ids), `Missing or ambiguous loaded set: ${taskId}`);
  const o = oracle.get(taskId);
  assert(o, `Missing task oracle: ${taskId}`);
  const unique = [...new Set(ids)];
  const items = unique.map(id => {
    const grade = o.grades.has(id) ? o.grades.get(id) : null;
    return {skill_id:id, grade, status:grade === null ? 'UNGRADED' : grade >= 2 ? 'RELEVANT' : 'NONRELEVANT'};
  });
  return {task_id:taskId, ...extra, loaded_skill_ids:unique, items, loaded:unique.length > 0,
    related:items.filter(x => x.status === 'RELEVANT').length,
    nonrelated:items.filter(x => x.status === 'NONRELEVANT').length,
    ungraded:items.filter(x => x.status === 'UNGRADED').length,
    oracle_relevant_count:o.relevant.length, oracle_none:o.relevant.length === 0};
}
const rows = tasks.map(t => {
  const codex = observations.tasks.find(x => x.id === t.id);
  assert(codex && !codex.load_return_conflict);
  const checks = codex.search_calls.flatMap(c => c.argument_observations.map(a => {
    const q = a.queries;
    return {call_id:c.id,event_sequence:a.event_sequence,query_count:q?.length,
      matches:Array.isArray(q) && q.length === 4 && q.every(s => typeof s === 'string') && q[3] === t.prompt};
  }));
  const claude = ['r1','r2','r3'].map(tag => {
    const matches = v2.sessions.filter(s => s.task_id === t.id && s.tag === tag);
    assert.equal(matches.length,1);
    const s = matches[0];
    assert.equal(s.prompt_matches,true);
    return classify(t.id,s.loaded_skill_ids,{tag,log_file:s.log_file,meta_file:s.meta_file,result_status:s.result_status});
  });
  return {task_id:t.id,repo:t.repo,prompt_characters:[...t.prompt].length,prompt_sha256:sha(t.prompt),
    at_least_800_characters:[...t.prompt].length >= 800,
    fourth_query_exact:checks.length > 0 && checks.every(c => c.matches),query_checks:checks,
    oracle_relevant_count:oracle.get(t.id).relevant.length,oracle_expect_none:oracle.get(t.id).expect_none,
    codex:classify(t.id,codex.confirmed_returned_skill_ids,{log_file:codex.evidence.transcript}),claude};
});
function metrics(sessions) {
  const loaded = sessions.filter(s => s.loaded);
  const hits = loaded.filter(s => s.related > 0);
  const unresolved = loaded.filter(s => s.related === 0 && s.ungraded > 0);
  const allItems = sessions.flatMap(s => s.items);
  const relevant = allItems.filter(i => i.status === 'RELEVANT').length;
  const negative = allItems.filter(i => i.status === 'NONRELEVANT').length;
  const unknown = allItems.filter(i => i.status === 'UNGRADED').length;
  const none = sessions.filter(s => s.oracle_none);
  return {sessions:sessions.length,loaded_sessions:loaded.length,hit_sessions:hits.length,
    unresolved_no_hit_sessions:unresolved.length,known_miss_sessions:loaded.length-hits.length-unresolved.length,
    loaded_pairs:allItems.length,relevant_pairs:relevant,nonrelevant_pairs:negative,ungraded_pairs:unknown,
    graded_pairs:relevant+negative,ungraded_sessions:loaded.filter(s => s.ungraded > 0).length,
    ungraded_unique_ids:new Set(allItems.filter(i => i.status === 'UNGRADED').map(i => i.skill_id)).size,
    hit_rate_confirmed:loaded.length ? hits.length/loaded.length : null,
    hit_rate_upper_bound:loaded.length ? (hits.length+unresolved.length)/loaded.length : null,
    precision_graded:relevant+negative ? relevant/(relevant+negative) : null,
    precision_lower_bound:allItems.length ? relevant/allItems.length : null,
    precision_upper_bound:allItems.length ? (relevant+unknown)/allItems.length : null,
    oracle_none_sessions:none.length,oracle_none_loaded_sessions:none.filter(s => s.loaded).length,
    oracle_none_loaded_pairs:none.reduce((n,s)=>n+s.items.length,0),
    oracle_none_ungraded_pairs:none.reduce((n,s)=>n+s.ungraded,0)};
}
const cohorts = {
  codex:metrics(rows.map(r => r.codex)),
  v2_r1:metrics(rows.map(r => r.claude[0])),
  v2_r2:metrics(rows.map(r => r.claude[1])),
  v2_r3:metrics(rows.map(r => r.claude[2])),
  v2_all:metrics(rows.flatMap(r => r.claude)),
};
const noneRows = rows.filter(r => r.oracle_relevant_count === 0);
const longRows = rows.filter(r => r.at_least_800_characters);
const classifiedUnknowns = rows.flatMap(r => [r.codex,...r.claude].flatMap(s => s.items.filter(i=>i.grade===null).map(i=>({task_id:r.task_id,session:s.tag ? `V2 ${s.tag}` : 'Codex',skill_id:i.skill_id}))));
const result = {schema_version:1,created_at:new Date().toISOString(),scope:'Offline oracle join; no new sessions, no new grades, no code-quality evaluation',
  counting_unit:'Unique (session, full skill ID) pairs; full task+ID exact match, including revision',
  inputs:Object.fromEntries([taskPath,oraclePath,observationsPath,v2Path].map(file=>[path.relative(base,file),sha(fs.readFileSync(file))])),
  report_before_sha256:sha(before),report_before_bytes:before.length,cohorts,
  long_task_ids:longRows.map(r=>r.task_id),oracle_no_relevant_task_ids:noneRows.map(r=>r.task_id),
  query_four_matches:rows.filter(r=>r.fourth_query_exact).length,ungraded_records:classifiedUnknowns,tasks:rows};
const percent = n => (100*n).toFixed(1)+'%';
const fraction = (n,d) => d ? `${n}/${d} (${percent(n/d)})` : `${n}/${d} (산출 불가)`;
const cell = s => {
  const contents = s.items.length ? s.items.map(i => '`'+i.skill_id+'` ('+(i.grade===null?'미채점':i.grade)+')').join('<br>') : '∅ (로드 없음)';
  return contents+'<br>[기록]('+path.relative(base,s.log_file)+')';
};
const c = cohorts.codex, v = cohorts.v2_all;
const out = ['', marker, '',
  '기존 Codex 19회와 Claude Code V2의 r1·r2·r3 기록 57회만 읽어 계산했다. 새 세션 실행·MCP 호출·추가 채점은 하지 않았다. 지정한 [stage5/oracle.jsonl](stage5/oracle.jsonl)의 `pool[].grade`를 유일한 판정 근거로 사용했다. `relevant_grades`와도 전수 대조해 충돌이 없음을 확인했다.', '',
  'V2는 같은 s5 기반에 아래 CLAUDE.md 한 줄을 추가한 조건이다. 두 레포의 기록된 V2 커밋과 해당 파일을 대조했다. V2 로그의 모델은 claude-opus-5-5[1m]이며, 성공 종료 41회와 error_max_turns 종료 16회를 모두 포함했다. 기록된 파일 조건은 검증했지만 stream-json만으로 개별 세션의 지침 주입 자체를 독립 입증한 것은 아니다.', '',
  '```text', v2.condition.expected_claude_line, '```', '',
  `**Codex에서 확인된 관련 스킬 적중은 ${fraction(c.hit_sessions,c.loaded_sessions)}, 채점된 로드만의 micro precision은 ${fraction(c.relevant_pairs,c.graded_pairs)}다.** 로드 ${c.loaded_pairs}건 중 ${c.ungraded_pairs}건(${c.ungraded_sessions}개 세션)은 미채점이다. 따라서 전체 로드 정밀도를 확정할 수 없으며, 확인된 적중만 전체 로드로 나눈 값은 ${fraction(c.relevant_pairs,c.loaded_pairs)}라는 하한이다.`, '',
  '### 계산 기준', '',
  '- 관련: 해당 태스크의 oracle 등급 ≥2. 태스크 ID와 revision을 포함한 전체 스킬 ID가 정확히 일치해야 한다. 다른 태스크의 등급을 가져오거나 ID의 해시를 지우지 않았다.',
  '- 로드 세트: `load_skills`의 실제 성공 반환 `skills[].id`를 세션 안에서 중복 제거했다. 요청한 ID, resolve 후보, 최종 발화의 주장만으로는 로드로 세지 않았다. 동일 스킬이 다른 세션에서 로드되면 각각 한 건이다.',
  '- 확인된 세션 적중률: 관련 스킬을 하나 이상 로드한 세션 / 스킬을 하나 이상 로드한 세션. 미채점만 있어 적중 여부가 미확정인 세션은 별도로 표시한다.',
  '- 채점된 로드 precision: 관련 로드 / 등급이 존재하는 전체 로드. 미채점은 분모에서 제외한다. 전체 로드 기준의 확인 적중 비율은 하한으로만 표시하며, 미채점을 0점으로 바꾸지 않는다.',
  '- “관련 스킬 없음”은 oracle에서 등급 ≥2인 항목이 0개인 태스크를 뜻한다. 이 4개를 포함해 `expect_none`은 19개 모두 false이므로 해당 플래그로 집계하지 않았다. oracle 밖 미채점 스킬까지 무관하다는 뜻은 아니다.', '',
  '### 관련성 지표', '',
  '| 집계 | 로드 세션 / 전체 | 확인 적중 / 로드 세션 | precision: 채점된 로드만 | 전체 로드 기준 확인 적중 하한 | 미채점 로드 / 전체 로드 | 미채점 포함 세션 |',
  '|---|---:|---:|---:|---:|---:|---:|'];
for(const [name,key] of [['Codex','codex'],['Claude V2 r1','v2_r1'],['Claude V2 r2','v2_r2'],['Claude V2 r3','v2_r3'],['Claude V2 합계','v2_all']]){
  const m=cohorts[key];out.push(`| ${name} | ${m.loaded_sessions}/${m.sessions} | ${fraction(m.hit_sessions,m.loaded_sessions)} | ${fraction(m.relevant_pairs,m.graded_pairs)} | ${fraction(m.relevant_pairs,m.loaded_pairs)} | ${m.ungraded_pairs}/${m.loaded_pairs} | ${m.ungraded_sessions} |`);
}
out.push('',
  `Codex의 ${c.loaded_sessions}개 로드 세션은 확인 적중 ${c.hit_sessions}개, 채점된 스킬만으로 확인된 비적중 ${c.known_miss_sessions}개, 확인 적중은 없고 미채점 스킬이 있어 미확정인 세션 ${c.unresolved_no_hit_sessions}개다. 미채점의 실제 등급을 모르므로 전체 세션 적중률의 가능한 범위는 ${percent(c.hit_rate_confirmed)}–${percent(c.hit_rate_upper_bound)}, 전체 로드 precision은 ${percent(c.precision_lower_bound)}–${percent(c.precision_upper_bound)}다. 이는 신뢰구간이 아니라 미채점 항목 때문에 생기는 산술적 범위다.`, '',
  `Claude V2 합계는 57회 중 ${v.loaded_sessions}회에서 로드했다. 로드하지 않은 세션도 원래 3회 비교표에서 제외하지 않았다. 종료 방식이 성공이 아니더라도 그 전에 실제 반환된 스킬은 포함했다. 두 조건은 모델·라우터 지침·세션 수·실행 한도 등이 다르므로 이 표만으로 모델 우열이나 지침의 인과 효과를 판정하지 않는다.`, '',
  '### oracle상 관련 스킬이 없는 태스크의 로드', '',
  `대상은 ${noneRows.map(r=>'`'+r.task_id+'`').join(', ')} 4개다. **Codex는 4/4개 태스크에서 총 ${c.oracle_none_loaded_pairs}개 스킬을 로드했다.** 이 중 ${c.oracle_none_loaded_pairs-c.oracle_none_ungraded_pairs}건은 등급 0–1, ${c.oracle_none_ungraded_pairs}건은 미채점이다.`, '',
  '| 집계 | 로드한 세션 / 해당 세션 | 로드 스킬 수 | 그중 미채점 |',
  '|---|---:|---:|---:|');
for(const [name,key] of [['Codex','codex'],['Claude V2 r1','v2_r1'],['Claude V2 r2','v2_r2'],['Claude V2 r3','v2_r3'],['Claude V2 합계','v2_all']]){
  const m=cohorts[key];out.push(`| ${name} | ${m.oracle_none_loaded_sessions}/${m.oracle_none_sessions} | ${m.oracle_none_loaded_pairs} | ${m.oracle_none_ungraded_pairs} |`);
}
out.push('', '### 요청 길이와 태스크별 로드 세트', '',
  `요청 길이는 tasks.jsonl.prompt의 Unicode 코드포인트 수이며 공백·줄바꿈을 포함한다. **800자 이상 요청은 ${longRows.length}/19개**: ${longRows.map(r=>'`'+r.task_id+'` '+r.prompt_characters+'자').join(', ')}. V2의 세 반복에선 같은 장문 요청이 ${longRows.length*3}/57회 등장한다. V2 57회 메타데이터의 실제 -p 인자가 이 요청과 모두 일치한다.`, '',
  `Codex의 네 번째 쿼리는 ${rows.filter(r=>r.fourth_query_exact).length}/19개 태스크에서 요청 원문과 정확히 일치했다. 검색 시작·완료의 인자 관찰 ${rows.reduce((n,r)=>n+r.query_checks.length,0)}개도 모두 일치하며, 800자 이상 요청 ${longRows.length}개도 포함한다. 이는 MCP 호출 인자 기준의 비교다.`, '',
  '괄호는 해당 태스크의 oracle 등급이며, 등급이 없으면 **미채점**으로 표시했다. `∅`는 실제 반환된 로드 세트가 비어 있다는 뜻이다. ★는 800자 이상 요청, “관련 후보 0”은 위의 oracle상 무관련 태스크다.', '',
  '| 태스크 | 요청 길이 | oracle 관련 후보 | Codex 4번째 쿼리 | Codex 로드 세트 | Claude V2 r1 | Claude V2 r2 | Claude V2 r3 |',
  '|---|---:|---:|---|---|---|---|---|');
for(const r of rows)out.push(`| ${r.task_id} | ${r.prompt_characters}${r.at_least_800_characters?' ★':''} | ${r.oracle_relevant_count} | ${r.fourth_query_exact?'원문 일치':'불일치/미확인'} | ${cell(r.codex)} | ${r.claude.map(cell).join(' | ')} |`);
out.push('', '### 미채점 및 재현 근거', '',
  `Codex의 미채점 ${c.ungraded_pairs}건은 ${c.ungraded_sessions}개 세션에 걸치며 고유 스킬 ID는 ${c.ungraded_unique_ids}개다. “미채점”은 태스크와 스킬의 쌍에 붙는다. 같은 스킬 ID라도 다른 태스크에서 받은 등급은 전용하지 않았다. Claude V2의 미채점은 ${v.ungraded_pairs}건, ${v.ungraded_sessions}개 세션이다. 모든 미채점 쌍과 반환 근거는 아래 JSON에 보존했다.`, '',
  'V2가 path: 형식으로 반환한 6건도 반환 ID 그대로 표시했다. 이를 비슷한 카탈로그 ID로 바꾸거나 등급을 추정하지 않고 미채점으로 유지했다.', '',
  '- [Codex·oracle 대조 및 지표 JSON](codex-e2e-2-oracle-analysis.json)',
  '- [Claude V2 57회 반환 추출 및 원시 행 근거](codex-e2e-2-oracle-v2.json)',
  '- [계산·추가 스크립트](codex-e2e-2-oracle-analysis.cjs)',
  '- oracle SHA256: `'+sha(fs.readFileSync(oraclePath))+'`.',
  `- 원래 보고서 ${before.length}바이트를 그대로 보존하고 이 절만 뒤에 추가했다. 기존 부분 SHA256: `+'`'+sha(before)+'`.',
  '- 작업 코드의 정확성이나 로드한 스킬의 실제 사용 여부는 평가하지 않았다. 다른 oracle·라벨 파일은 이 계산에 사용하지 않았다.', '');
const after = Buffer.concat([before, Buffer.from(out.join('\n'),'utf8')]);
assert(after.subarray(0,before.length).equals(before));
assert.equal(sha(fs.readFileSync(reportPath)),sha(before),'Report changed during analysis');
result.report_after_sha256=sha(after);
result.report_after_bytes=after.length;
fs.writeFileSync(artifactPath,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
const temporary=reportPath+'.oracle-append.tmp';
fs.writeFileSync(temporary,after,{flag:'wx'});
fs.renameSync(temporary,reportPath);
console.log(JSON.stringify({status:'PASS',cohorts,long_tasks:result.long_task_ids,query_four_matches:result.query_four_matches,report:reportPath},null,2));
