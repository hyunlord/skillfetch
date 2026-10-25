'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const base = __dirname;
const run = path.join(base, 'codex-e2e-runs/20261024-subscription-mcp-approved-14d2020');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const obs = read(path.join(run, 'observations.json'));
const audit = read(path.join(run, 'audit-verification.json'));
const manifest = read(path.join(run, 'manifest.json'));
const smoke = read(path.join(base, 'codex-e2e-2-smoke/verification.json'));
const tasks = obs.tasks;
const ensure = (ok, msg) => { if (!ok) throw Error(msg); };
ensure(tasks.length === 19 && new Set(tasks.map(t => t.id)).size === 19, 'Expected 19 unique observations');
ensure(audit.status === 'PASS' && smoke.status === 'PASS', 'Verification must pass before report');
ensure(manifest.status === 'COMPLETED', 'Measured run must be completed');
const oldHash = crypto.createHash('sha256').update(fs.readFileSync(path.join(base, 'codex-e2e.md'))).digest('hex');
ensure(oldHash === 'db5b22600f4d20048f5669a39221335d8b5f7106cd1824d4b2deb57848d139c5', 'Previous report changed');
const rel = file => path.relative(base, file);
const runRel = rel(run);
const link = (label, file) => `[${label}](${rel(file)})`;
const code = value => '`' + String(value).replaceAll('`', '\\`').replaceAll('|', '\\|') + '`';
const percent = n => `${n}/19 (${(100*n/19).toFixed(1)}%)`;
const count = predicate => tasks.filter(predicate).length;
const sum = field => tasks.reduce((n,t) => n + (t[field] || 0), 0);
const searches = tasks.flatMap(t => t.search_calls.map(c => ({task:t.id,...c})));
const loads = tasks.flatMap(t => t.load_calls.map(c => ({task:t.id,...c})));
const callsByTool = {};
for(const t of tasks)for(const c of t.calls)callsByTool[c.tool] = (callsByTool[c.tool] || 0) + 1;
const loaded = tasks.filter(t => (t.confirmed_returned_skill_ids || t.returned_skill_ids || []).length > 0);
const searchPass = searches.filter(c => c.query_check_status === 'PASS').length;
const lines = [];
const add = (...s) => lines.push(...s);
add('Codex CLI 0.164.0 | 모델: gpt-6-astra (reasoning: medium) | 인증: ChatGPT Pro 구독 로그인 (`chatgpt`), API 키 환경변수 미상속', '',
  '# Codex E2E 재실행: skillfetch 전용 자동 승인', '',
  `같은 19개 태스크를 각각 한 번 실행했다. **발화율은 ${percent(count(t => t.skillfetch_called))}**다. 발화는 모델이 skillfetch 도구 호출을 요청한 세션을 뜻한다. 실제 MCP 프로토콜 성공 응답을 받은 세션은 **${count(t => t.successful_server_call_count > 0)}/19**, 반환된 스킬 ID가 확인된 세션은 **${loaded.length}/19**다. 승인 차단은 **${sum('approval_denied_call_count')}건**이었다.`, '',
  '이번 변경은 skillfetch 서버의 MCP 도구 승인 설정 한 줄이다. 전역 `approval_policy = "never"`, `workspace-write`, 셸 네트워크 차단 등 나머지 설정과 라우터 AGENTS.md는 이전 실행과 같다. 코딩 결과물은 평가하지 않았다.', '',
  '| 지표 | 결과 |', '|---|---:|',
  '| 실제 태스크 제출 | 19개, 각 1회 |',
  `| skillfetch 호출 요청 세션 | ${percent(count(t => t.skillfetch_called))} |`,
  `| MCP 성공 응답 세션 | ${percent(count(t => t.successful_server_call_count > 0))} |`,
  `| search_skills 호출 세션 / 호출 수 | ${count(t => t.search_calls.length > 0)}/19 / ${searches.length}회 |`,
  `| 네 번째 질의가 원문과 일치한 검색 호출¹ | ${searchPass}/${searches.length} |`,
  `| load_skills 호출 세션 / 호출 수 | ${count(t => t.load_calls.length > 0)}/19 / ${loads.length}회 |`,
  `| 실제 반환 ID가 확인된 세션 | ${loaded.length}/19 |`,
  `| 반환 ID 건수 / 고유 ID | ${tasks.reduce((n,t)=>n+(t.confirmed_returned_skill_ids || []).length,0)} / ${new Set(tasks.flatMap(t=>t.confirmed_returned_skill_ids || [])).size} |`,
  `| load 반환 관찰 충돌 | ${loads.filter(c => c.return_conflict).length}회 |`,
  `| 정상적인 모델 최종 응답으로 종료 | ${count(t => t.status === 'COMPLETED')}/19 |`,
  `| worktree 정리 완료 | ${count(t => t.manifest.cleanup === 'DONE')}/19 |`, '',
  `도구별 호출 수: ${Object.entries(callsByTool).map(([k,v]) => `${code(k)} ${v}회`).join(', ')}. 전체 호출 ${sum('skillfetch_call_attempt_count')}회 중 서버 결과 ${sum('server_result_count')}회, 프로토콜 성공 ${sum('successful_server_call_count')}회다. 정상 프로토콜 응답 안의 도메인 오류는 별도로 아래 기록한다.`, '',
  '¹ 모든 lifecycle 인자 관찰에서 `queries.length === 4`, 모든 값이 문자열, `queries[3] === tasks.jsonl의 prompt`를 검사했다. 공백·줄바꿈·Unicode를 정규화하지 않았다. 미호출은 일치로 세지 않는다.', '',
  '## 정확한 설정과 사전 검증', '',
  '각 세션의 격리된 `$CODEX_HOME/config.toml`에 다음 설정을 사용했다. 이전 입력에서 추가한 것은 `[mcp_servers.skillfetch]`의 `default_tools_approval_mode = "approve"` 한 줄뿐이며, 그 줄을 제거하면 이전 config와 바이트 단위로 일치한다. 이 설정은 등록된 skillfetch의 네 도구에만 적용된다. [공식 MCP 설정 문서](https://learn.chatgpt.com/docs/extend/mcp)의 서버별 승인 옵션을 설치된 CLI에서 확인했다.', '',
  '```toml', fs.readFileSync(path.join(run,'config.input.toml'),'utf8').trimEnd(), '```', '',
  '검증 명령은 동일한 격리 환경에서 실행했다:', '',
  '```sh', 'codex mcp get skillfetch', 'codex app-server --strict-config --print-startup-config', '```', '',
  'plain `mcp get` 출력의 `default_tools_approval_mode: approve`를 확인했다. `mcp get --json`에는 이 승인 필드가 빠지므로 판정에 쓰지 않았다. 실행 thread의 유효 전역 승인 정책과 sandbox도 별도로 검증했다. 승인 요청 콜백에서 모든 요청을 허용하는 처리나 추가 대화는 넣지 않았다.', '',
  'Codex는 실행 중 config 끝에 해당 템플릿 레포의 `trust_level = "trusted"` 메타데이터를 자동 추가했다. 이전 실행의 해당 태스크에도 같은 메타데이터가 있어, 이전·이번 최종 config 사이의 차이는 MCP 승인 한 줄뿐이었다. 최초 검증기는 입력 config와 최종 config의 바이트 동일성을 요구해 이 19건을 실패로 기록했다. 기존 메타데이터와의 정확한 일치를 검사하도록 검증기를 수정했으며, 최초 실패 기록은 삭제하지 않았다. '+link('최초 검증 기록',path.join(run,'audit-verification-initial.json'))+' · '+link('최종 검증',path.join(run,'audit-verification.json')), '',
  '본 실험 전에 별도 ChatGPT 구독 세션에서 **모델이 직접** `profile_repo → search_skills → resolve_set → load_skills`를 호출하도록 했다. 네 호출 모두 실제 결과를 받았고, `uasl/api-testing@4ada9a2fac88`가 로드됐다. 이 사전 검증은 19개 태스크 분모에 포함하지 않았다. '+link('사전 검증 결과',path.join(base,'codex-e2e-2-smoke/verification.json'))+' · '+link('원시 기록',path.join(base,'codex-e2e-2-smoke/transcript.jsonl')), '',
  '## 세션별 기록', '',
  '“호출”은 모델의 요청 횟수다. 첫 호출 턴은 아래 설명한 모델 응답 회차다. ID는 load 요청의 ID가 아니라 성공한 반환 payload의 `skills[].id`에서 추출했다. `COMPLETED`는 모델이 최종 응답으로 종료했다는 뜻이다.', '',
  '| 태스크 | 레포 | skillfetch 호출 | 첫 호출 턴² | queries 원문 | 4번째=요청 원문 | load_skills 반환 ID | 끝난 방식 | 정리 |',
  '|---|---|---:|---:|---|---|---|---|---|');
for(const t of tasks){
  const ids = t.confirmed_returned_skill_ids || t.returned_skill_ids;
  const q = !t.search_calls.length ? '미호출' : t.search_calls.map(c=>c.query_check_status==='PASS'?'일치':c.query_check_status).join(', ');
  const idText = t.load_return_conflict ? '충돌: 반환 관찰 참조' : ids?.length ? ids.map(code).join('<br>') : '`[]`';
  add(`| ${link(t.id,t.evidence.transcript)} | ${t.repo} | ${t.skillfetch_called?'예':'아니오'} (${t.skillfetch_call_count}회) | ${t.first_call?.model_response_cycle ?? '미확인'} | ${t.search_calls.length?`[${t.search_calls.length}회 원문](#queries-${t.id})`:'없음'} | ${q} | ${idText} | ${code(t.status)} | ${code(t.manifest.cleanup)} |`);
}
add('', `첫 호출은 ${tasks.filter(t=>t.first_call?.tool==='profile_repo').length}/19개 세션에서 profile_repo였고, ${tasks.filter(t=>t.first_call?.model_response_cycle===2).length}/19개에서 모델 응답 회차 2로 추론됐다.`, '', '² “턴”은 고유 `rawResponse/completed.responseId`의 1-based 순서다. 외부 사용자 턴은 세션마다 1회다. MCP 호출은 `functions.exec` 안에서 수행되어 부모 ID가 직접 제공되지 않는 경우가 있다. 이때 같은 thread/turn에서 MCP 시작·완료를 감싸는 유일하게 닫힌 exec 구간과 코드의 도구 이름을 대조해 회차를 추론했다. 직접 연결인지 추론인지 및 근거 sequence는 관찰 JSON의 `first_call`에 보존했다. 애매하면 미확인으로 남긴다. Stage 4의 assistant-message 순번과 같은 단위로 취급하지 않는다.', '',
  '## 반환 오류와 관측 한계', '');
const exceptional = loads.filter(c=>c.semantic_status!=='SUCCESS'||c.protocol_status!=='SUCCESS'||c.return_conflict);
if(!exceptional.length)add('load_skills의 프로토콜 오류, payload `error`/`errors`, 반환 관찰 충돌은 발견되지 않았다.');
else for(const c of exceptional)add(`- ${c.task}, ${code(c.id)}: protocol=${code(c.protocol_status)}, semantic=${code(c.semantic_status)}, conflict=${c.return_conflict}. 원시 반환과 스킬 ID의 출처는 관찰 JSON의 해당 load_calls에 보존했다.`);
add('', 'AGENTS.md는 이전과 같은 1–4단계이며 1–3개 스킬 선택까지 명시한다. 측정을 위해 추가 load 지시나 후속 사용자 메시지를 넣지 않았다. 로드된 스킬 내용의 유용성·적용 여부·코드 정확성은 평가하지 않았다. 단일 실행 19개 표본이므로 일반적인 Codex 전체 성공률이나 다른 모델의 성능으로 일반화하지 않는다.', '',
  '## 고정 조건·재현 기록', '',
  `- skillfetch: ${code(manifest.source_commit)}. 고정 소스 238개와 인덱스 6개의 해시를 세션마다 검증했다.`,
  `- FastAPI s5: ${code(manifest.repository_refs.fastapi)}.`,
  `- Next.js s5: ${code(manifest.repository_refs.nextjs)}.`,
  `- 태스크: FastAPI 17개·Next.js 2개. tasks SHA256 ${code(manifest.tasks_sha256)}.`,
  `- AGENTS SHA256: ${code(manifest.agents_sha256)}. 새 config SHA256: ${code(manifest.config_sha256)}.`,
  '- 각 태스크는 s5 커밋의 새 detached worktree, 새 ephemeral thread, 격리된 HOME/CODEX_HOME을 사용했다. s5 브랜치를 새로 만들지 않았다. MCP는 skillfetch만 등록했다.',
  '- 세션 환경은 PATH, HOME, CODEX_HOME, TMPDIR와 선택적인 LANG/LC_ALL/TERM만 전달했다. OPENAI_API_KEY 등 API 키 변수는 상속하지 않았다. forced_login_method="chatgpt", login status, account/read(chatgpt/pro)를 각 세션에서 확인했다.',
  '- 기본 Codex 추론은 허용된 ChatGPT 구독 인증을 사용했다. API 키 기반 호출은 실행하지 않았다. 셸 네트워크 접근은 이전과 같이 차단했다. MCP 스킬 본문 조회는 이전과 같은 서버 환경을 사용했다.',
  `- 동시 실행 ${manifest.concurrency}개, 세션 제한 ${manifest.timeout_seconds}초, 모델 응답 회차 상한 없음. 태스크 프롬프트 재제출·재시도 없음. 별도 사전 검증 1회.`,
  `- 실행 시간(UTC): ${manifest.created_at} ~ ${manifest.finished_at}.`,
  '- 각 세션 종료 후 worktree와 Git worktree 등록, 인증 symlink를 제거했다. 실험의 임시 worktree 루트도 제거했다. 고정 소스·인덱스와 측정 기록은 재현 근거로 보존했다.',
  `- 이전 ${link('codex-e2e.md',path.join(base,'codex-e2e.md'))} SHA256: ${code(oldHash)}. 이전 보고서는 변경하지 않았다.`, '',
  '실행 명령:', '', '```sh',
  'node codex-e2e-2-runner.cjs \\',
  '  --run-dir codex-e2e-runs/20261024-subscription-mcp-approved-14d2020 \\',
  '  --config-template codex-e2e-2-preparation/config-template.toml \\',
  '  --agents-file codex-e2e-2-preparation/AGENTS.md \\',
  '  --source-preflight codex-e2e-2-preparation/source-preflight.json \\',
  '  --cloud-skills-snapshot codex-e2e-2-preparation/cloud-skills.json \\',
  '  --auth-file "<home>/Library/Application Support/orca/codex-accounts/54be5844-95fd-4c46-925c-75327ccd186a/home/auth.json" \\',
  '  --model gpt-6-astra --concurrency 4 --allow-codex-inference', '```', '',
  '위 명령의 기준 디렉터리는 `<e2e>`다. 실행마다 새 run-dir이 필요하며, 기존 경로 재사용은 중복 제출 방지를 위해 거부한다.', '',
  `${link('실행 manifest',path.join(run,'manifest.json'))} · ${link('전체 관찰 JSON',path.join(run,'observations.json'))} · ${link('독립 전수 검증',path.join(run,'audit-verification.json'))} · ${link('실행기',path.join(base,'codex-e2e-2-runner.cjs'))} · ${link('추출기',path.join(base,'codex-e2e-2-extract.cjs'))}`, '',
  '## search_skills에 넘긴 queries 원문', '',
  '다음 값은 실제 도구 인자에서 추출했으며 재생성·번역·요약하지 않았다. 같은 호출의 시작/완료에 반복된 동일 인자는 배열을 한 번만 싣고 모든 관찰 sequence를 나열했다. 인자가 서로 다르면 각각 별도로 남긴다.', '');
for(const t of tasks){
  if(!t.search_calls.length)continue;
  add(`### queries-${t.id}`,'');
  for(const c of t.search_calls){
    add(`호출 ${code(c.id)} · 질의 검증 ${code(c.query_check_status)}.`, '');
    const variants = new Map();
    for(const a of c.argument_observations){
      const key = JSON.stringify(a.arguments);
      if(!variants.has(key))variants.set(key,{arguments:a.parsed_arguments ?? a.arguments,sequences:[]});
      variants.get(key).sequences.push(a.event_sequence);
    }
    for(const a of variants.values())add(`원시 sequence: ${a.sequences.join(', ')}.`, '', '```json', JSON.stringify(a.arguments?.queries ?? a.arguments,null,2), '```', '');
  }
}
const target = path.join(base,'codex-e2e-2.md');
fs.writeFileSync(target,lines.join('\n')+'\n',{flag:'wx'});
console.log(JSON.stringify({report:target,task_count:tasks.length,firing_count:count(t=>t.skillfetch_called),search_calls:searches.length,query_pass:searchPass,loaded_sessions:loaded.length}));
