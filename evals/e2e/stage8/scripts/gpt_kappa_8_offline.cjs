// Offline-only Stage 8 cross-judge analysis. No imports of experiment runners.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const base = path.resolve(__dirname, '../..');
const hashes = {};
function read(f) { const b = fs.readFileSync(path.join(base, f)); hashes[f] = crypto.createHash('sha256').update(b).digest('hex'); return b.toString('utf8'); }
function json(f) { return JSON.parse(read(f)); }
function lines(f) { return read(f).trim().split('\n').map(JSON.parse); }
function keyed(rows, key) { const obj = {}; for (const row of rows) { const k = key(row); assert(!Object.hasOwn(obj,k), `duplicate ${k}`); obj[k]=row; } return obj; }
const blind=lines('stage8/blind-ss-60.jsonl');
const pairKey=r=>`${r.task_id}/${r.candidate_id}`;
const gpt=keyed(lines('stage8/gpt-ss-60.jsonl'),pairKey);
const blindMap=keyed(blind,pairKey);
assert.deepEqual(Object.keys(gpt).sort(),Object.keys(blindMap).sort());
const labels=json('stage8/grade-labels.json'), cands=json('stage8/cands.json');
const oracle=keyed(lines('stage8/oracle-v5-ss.jsonl'),r=>r.id);
const tasks=keyed(lines('stage3/tasks.jsonl'),r=>r.id);
const rc=json('stage6/gen/results-rc.json'), ssMap=json('stage8/ss-map.json');
const raw=keyed(lines('stage8/raw/main.jsonl'),r=>`${r.task}/${r.kind}`);
const selections=['select-S-bp.jsonl','select-S-bp-rep2.jsonl','select-S-bp-rep3.jsonl'].map(f=>keyed(lines(`stage6/${f}`),r=>r.id));
read('stage8/metrics-8.json'); // Protect the pre-existing report inputs against accidental changes.
const T=[...new Set(blind.map(r=>r.task_id))].sort();
assert.equal(T.length,60); assert.equal(blind.length,2270);
const opus={};
for(const t of T) {
 opus[t]=keyed(oracle[t].pool,r=>r.label);
 assert.deepEqual(Object.keys(opus[t]).sort(),blind.filter(r=>r.task_id===t).map(r=>r.candidate_id).sort());
 assert.deepEqual([...new Set(oracle[t].pool.filter(r=>r.grade>=2).map(r=>r.skill))].sort(),[...oracle[t].relevant].sort());
 assert.equal(tasks[t].expect_none,oracle[t].expect_none);
}
const pairs=blind.map(b=>{
 const t=b.task_id, o=opus[t][b.candidate_id], g=gpt[pairKey(b)], skill=labels[t][b.candidate_id], c=cands[t][skill];
 assert.equal(skill,o.skill); assert.deepEqual([...o.sources].sort(),[...c.sources].sort());
 assert.equal(b.title,c.title); assert.equal(b.summary,c.summary);
 for(const r of [o,g]) { assert(Number.isInteger(r.grade)&&r.grade>=0&&r.grade<=3); assert.equal(typeof r.process,'boolean'); }
 const sf=c.sources.some(s=>s.startsWith('SF-')), ss=c.sources.some(s=>s.startsWith('SS-'));
 assert(sf||ss);
 return {task_id:t,candidate_id:b.candidate_id,skill,title:b.title,sources:c.sources,source:sf?(ss?'both':'SF-only'):'SS-only',identity:skill.startsWith('ss:')?'SS-unmerged':'SF-index',opus_grade:o.grade,gpt_grade:g.grade,opus_process:o.process,gpt_process:g.process};
});
function agreement(P,field) {
 const cells={neither:0,gpt_only:0,opus_only:0,both:0};
 for(const p of P) {const o=field==='relevance'?p.opus_grade>=2:p.opus_process,g=field==='relevance'?p.gpt_grade>=2:p.gpt_process;cells[o?(g?'both':'opus_only'):(g?'gpt_only':'neither')]++;}
 const n=P.length, po=(cells.neither+cells.both)/n, op=(cells.both+cells.opus_only)/n,gp=(cells.both+cells.gpt_only)/n,pe=op*gp+(1-op)*(1-gp);
 return {n,...cells,opus_positive:cells.both+cells.opus_only,gpt_positive:cells.both+cells.gpt_only,observed_agreement:po,expected_agreement:pe,kappa:n&&pe<1?(po-pe)/(1-pe):null,gpt_only_rate:cells.gpt_only/n,opus_only_rate:cells.opus_only/n,net_gpt_minus_opus:(cells.gpt_only-cells.opus_only)/n};
}
const sourceStats=Object.fromEntries(['SF-only','SS-only','both'].map(s=>[s,agreement(pairs.filter(p=>p.source===s),'relevance')]));
const identityStats=Object.fromEntries(['SF-index','SS-unmerged'].map(s=>[s,agreement(pairs.filter(p=>p.identity===s),'relevance')]));
const taskSource=T.map(t=>({task_id:t,...Object.fromEntries(['SF-only','SS-only','both'].map(s=>[s,agreement(pairs.filter(p=>p.task_id===t&&p.source===s),'relevance')]))}));
const key=sid=>ssMap[sid]?.merged_into||`ss:${sid.toLowerCase()}`;
const ranks={SF:{},'SS-q1':{},'SS-q3':{},'SS-kw':{}};
const loads={'SF r1':{},'SF r2':{},'SF r3':{},'SS-load-kw':{},'SS-load-full':{}};
for(const t of T) {
 ranks.SF[t]=rc[t].results.map(r=>r.id);
 for(const kind of ['SS-q1','SS-q3','SS-kw']) {
  const r=raw[`${t}/${kind}`]; assert(!r.error&&!r.is_error);
  ranks[kind][t]=r.text.split(/^### /m).slice(1).flatMap(blk=>{const m=blk.match(/load_skill` with id `([^`]+)`/);return m?[key(m[1])]:[];});
 }
 for(let i=0;i<3;i++) {assert(selections[i][t]); loads[`SF r${i+1}`][t]=[...new Set(selections[i][t].skills)];}
 for(const kind of ['SS-load-kw','SS-load-full']) {
  const r=raw[`${t}/${kind}`]; assert(!r.error&&!r.is_error);
  const found=Object.entries(cands[t]).filter(([,c])=>c.sources.includes(kind)).map(([k])=>k);
  assert.equal(found.length,/^# Skill loaded: (.+?)\s+\(([^)]+)\)/.test(r.text)?1:0);
  loads[kind][t]=found;
 }
 for(const ranking of Object.values(ranks)) for(const s of ranking[t].slice(0,10)) assert(cands[t][s],`ungraded rank ${t} ${s}`);
 for(const load of Object.values(loads)) for(const s of load[t]) assert(cands[t][s],`ungraded load ${t} ${s}`);
}
const R={opus:{},intersection:{},gpt:{}};
for(const t of T) {
 R.opus[t]=new Set(oracle[t].relevant);
 R.gpt[t]=new Set(pairs.filter(p=>p.task_id===t&&p.gpt_grade>=2).map(p=>p.skill));
 R.intersection[t]=new Set(pairs.filter(p=>p.task_id===t&&p.opus_grade>=2&&p.gpt_grade>=2).map(p=>p.skill));
}
const ratio=(n,d)=>({n,d,rate:d?n/d:null});
function evaluate(R, fixedRel=null) {
 const rel=fixedRel||T.filter(t=>!tasks[t].expect_none&&R[t].size), irr=T.filter(t=>!rel.includes(t));
 const table1=Object.fromEntries(Object.entries(ranks).map(([c,rank])=>[c,Object.fromEntries([1,5,10].map(k=>[`@${k}`,ratio(rel.filter(t=>rank[t].slice(0,k).some(s=>R[t].has(s))).length,rel.length)]))]));
 const final_load=Object.fromEntries(Object.entries(loads).map(([c,L])=>{
  const hit=rel.filter(t=>L[t].some(s=>R[t].has(s))).length, loaded=rel.filter(t=>L[t].length).length;
  return [c,{hit:ratio(hit,rel.length),hit_over_loaded:ratio(hit,loaded),irrelevant_loaded:ratio(irr.filter(t=>L[t].length).length,irr.length),expect_none_loaded:ratio(T.filter(t=>tasks[t].expect_none&&L[t].length).length,T.filter(t=>tasks[t].expect_none).length),mean_loaded_all:ratio(T.reduce((n,t)=>n+L[t].length,0),T.length),mean_loaded_relevant:ratio(rel.reduce((n,t)=>n+L[t].length,0),rel.length)}];
 }));
 const sf=Object.values(final_load).slice(0,3);
 final_load['SF pooled 3 runs']=Object.fromEntries(Object.keys(sf[0]).map(k=>[k,ratio(sf.reduce((n,r)=>n+r[k].n,0),sf.reduce((n,r)=>n+r[k].d,0))]));
 return {relevant_tasks:rel,irrelevant_tasks:irr,table1,final_load};
}
const O=evaluate(R.opus), I=evaluate(R.intersection), F=evaluate(R.intersection,O.relevant_tasks);
const out={method:'grade>=2; unweighted binary Cohen kappa; task-local labels; retrieval provenance is union of search and selection/load sources; no API or new sessions',rows:pairs.length,tasks:T.length,exact:ratio(pairs.filter(p=>p.opus_grade===p.gpt_grade).length,pairs.length),within1:ratio(pairs.filter(p=>Math.abs(p.opus_grade-p.gpt_grade)<=1).length,pairs.length),relevance:agreement(pairs,'relevance'),process:agreement(pairs,'process'),by_source:sourceStats,by_identity:identityStats,opus:O,intersection:I,intersection_fixed_opus_denominator:F,gpt_fixed_opus_denominator:evaluate(R.gpt,O.relevant_tasks),lost_relevant_tasks:O.relevant_tasks.filter(t=>!I.relevant_tasks.includes(t)),task_source:taskSource,task_ids:T,pairs,ranks,loads,input_sha256:hashes};
for(const [f,h] of Object.entries(hashes)) assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(base,f))).digest('hex'),h);
fs.writeFileSync(path.join(base,'stage8/gpt-kappa-8.json'),JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify({rows:out.rows,tasks:out.tasks,relevance_kappa:out.relevance.kappa,process_kappa:out.process.kappa,lost:out.lost_relevant_tasks}));
const fmt=x=>x===null?'N/A':x.toFixed(3);
const cell=r=>`${fmt(r.rate)} (${r.n}/${r.d})`;
const pct=x=>`${(100*x).toFixed(2)}%`;
const signed=x=>`${x>=0?'+':''}${(100*x).toFixed(2)}%p`;
const md=[];
md.push('# Stage 8 후속: GPT × Opus v5-ss 교차 판정', '',
'60태스크·2,270 후보 쌍. 기존 로컬 파일만 계산했으며 외부 API 호출, 신규 세션 실행, 재채점은 하지 않았다. 원본 라벨과 기존 `metrics-8.json`·`report-8.md`는 수정하지 않았다.', '',
'## 핵심 결과', '',
`- 관련 여부 Cohen κ = **${fmt(out.relevance.kappa)}**, process κ = **${fmt(out.process.kappa)}**. 등급 완전 일치 ${cell(out.exact)}, ±1 일치 ${cell(out.within1)}.`,
'- 불일치 방향은 대칭이 아니다. GPT만 관련 / Opus만 관련은 SF 전용 **73 / 2**, SS 전용 **103 / 36**이다. 출처별 전체 후보로 나누면 GPT의 순증은 SF **+11.18%p**, SS **+4.10%p**로 SF 쪽이 **7.08%p** 더 크다.',
'- 교집합에서도 SS-kw의 hit@10 우세는 유지된다: SS 42/52, SF 20/52. 최종 관련 적중도 SS-load-kw 28/52(0.538), SF 3회 평균 0.468이다.',
'- 그러나 이것만으로 판정자 영향이 작다고 결론내릴 수 없다. 같은 52태스크에서 GPT 단독으로 계산하면 SF 최종 적중 평균 **0.654**, SS-load-kw **0.596**으로 순서가 뒤집힌다. Opus 단독은 각각 0.481, 0.577이다. 교집합은 GPT만 인정한 후보를 버리므로 이 방향의 민감도를 숨긴다.', '',
'## 1. 결합·정의·분모', '',
'`(task_id, candidate_id)`로 GPT와 블라인드 카드를 결합했다. `grade-labels.json`으로 실제 스킬 ID를 복원하고 `oracle-v5-ss.jsonl`의 label·skill·sources와 `cands.json`의 title·summary·sources가 일치하는지 확인했다. 후보 ID는 태스크마다 재사용되므로 ID 단독 결합은 하지 않았다.', '',
'관련 = 등급 ≥2. 교집합 = 같은 후보에 두 판정자가 모두 ≥2. process는 별도 boolean이며 관련 판정의 필터로 쓰지 않았다. κ는 이진·비가중 Cohen κ, `(관측 일치율 − 우연 기대 일치율)/(1 − 우연 기대 일치율)`이다. 후보 쌍 단위 micro 집계이며 반복 스킬·동일 태스크 내 후보를 독립 표본으로 가정한 유의확률은 산출하지 않았다.', '',
`두 라벨 모두 관련 태스크 **${O.relevant_tasks.length}**, 무관련 태스크 **${O.irrelevant_tasks.length}**로 동일하다. 관련 분모는 expect_none이 아니고 관련 후보가 한 개 이상인 태스크다. 무관련 8개 중 expect_none은 6개다. 교집합으로 바뀌며 관련 분모에서 탈락한 태스크는 없다. 따라서 아래 차이는 분모 변화가 아니다.`, '',
`무관련 태스크: ${O.irrelevant_tasks.join(', ')}. 전체 60태스크를 사용하되 hit@k와 관련 적중률의 분모는 52, 무관련 로드율의 분모는 8이다.`, '',
'## 2. 일치도', '',
'| 판정 | 둘 다 false | GPT만 true | Opus만 true | 둘 다 true | 관측 일치율 | 기대 일치율 | κ |',
'|---|---:|---:|---:|---:|---:|---:|---:|');
for(const [name,a] of [['관련 여부',out.relevance],['process',out.process]]) md.push(`| ${name} | ${a.neither} | ${a.gpt_only} | ${a.opus_only} | ${a.both} | ${fmt(a.observed_agreement)} | ${fmt(a.expected_agreement)} | ${fmt(a.kappa)} |`);
md.push('', '관련 후보: Opus 355/2,270, GPT 493/2,270, 교집합 317/2,270. process=true: Opus 390, GPT 666. process의 큰 순증은 관련 판정과 별개인 분류 기준 차이도 있음을 보여준다.', '',
'## 3. 출처별 불일치 방향', '',
'출처는 스킬 ID 접두사가 아니라 `cands.json.sources`의 실제 유입 경로로 정의했다. SF = SF-top10 또는 SF-sel-r1/r2/r3, SS = SS-q1/q3/kw 또는 SS-load-kw/full. 둘 다 있으면 공통으로 따로 세며 이 60태스크에서는 공통 후보가 0개다. 이는 전체 380태스크에 공통 후보가 없다는 뜻은 아니다.', '',
'| 유입 출처 | 후보 수 | Opus 관련 | GPT 관련 | 둘 다 관련 | GPT만 관련 (출처 내 비율) | Opus만 관련 (출처 내 비율) | GPT−Opus 순증 | 관련 κ |',
'|---|---:|---:|---:|---:|---:|---:|---:|---:|');
for(const s of ['SF-only','SS-only']) {const a=sourceStats[s];md.push(`| ${s} | ${a.n} | ${a.opus_positive} (${pct(a.opus_positive/a.n)}) | ${a.gpt_positive} (${pct(a.gpt_positive/a.n)}) | ${a.both} | ${a.gpt_only} (${pct(a.gpt_only_rate)}) | ${a.opus_only} (${pct(a.opus_only_rate)}) | ${signed(a.net_gpt_minus_opus)} | ${fmt(a.kappa)} |`);}
md.push('| 공통 | 0 | 0 | 0 | 0 | 0 (N/A) | 0 (N/A) | N/A | N/A |', '',
'GPT만 관련 176건 중 SS가 103건(58.52%)으로 건수는 더 많지만, 원래 SS 후보가 전체의 72.03%를 차지한다. SF는 전체 후보의 27.97%인데 GPT만 관련의 41.48%를 차지한다. 따라서 원시 건수만 보고 GPT의 관대함이 SS에 더 몰렸다고 해석하면 반대 결론이 된다. 반면 Opus만 관련 38건 중 **36건(94.74%)은 SS**다.', '',
'Opus가 관련으로 인정한 후보가 교집합에서 유지되는 비율은 SF 54/56 = 96.43%, SS 263/299 = 87.96%다. 교집합은 Opus 관련 후보 중 SF 2개, SS 36개를 제외하지만, GPT만 관련인 SF 73개·SS 103개를 새로 인정하지 않는다.', '',
'태스크마다 동일한 가중치를 주어 각 출처의 `(GPT만−Opus만)/후보 수`를 평균해도 SF +10.99%p, SS +3.14%p로 방향은 같다. SF에서 GPT 순증 / Opus 순증 / 동률 태스크 수는 38/2/20, SS는 31/12/17이다.', '',
'ID 소속으로 다시 나누면 SF-index 636, SS-unmerged 1,634다. 유입 출처와 다른 1건은 t083/c08 `anthropics-skills/frontend-design@0a5ff23f1022`: SS-q3로만 들어왔지만 기존 index ID로 병합됐고 두 판정자 모두 0점이다. 따라서 이 분류 차이는 불일치 건수와 방향을 바꾸지 않는다.', '',
'해석: 이 표본에서는 GPT가 Opus보다 SF 출처 후보에 상대적으로 더 관대하다. 즉 Opus 단독 기준은 GPT 기준과 비교할 때 SS 쪽에 상대적으로 유리하게 작용한다. 이것이 어느 판정자가 정답이라는 증거는 아니다. 출처는 블라인드였지만 후보 내용·process 비중·요약 방식이 다르며, SS 설명은 공급자 요약, SF 설명은 frontmatter에서 왔다(`report-8.md`의 설명 생성 한계). 이 분석만으로 의도적 시스템 선호나 전체 380태스크의 편향 크기를 확정할 수 없다.', '',
'## 4. 표 1: Opus 단독 vs 교집합', '',
'동일한 저장 순위를 그대로 사용했다. SS ID는 저장된 `ss-map.json.merged_into`로만 정규화했다. 관련 적중은 상위 k개 중 관련 후보가 하나 이상인 태스크 수 / 52다. 아래 각 셀은 비율 (분자/분모).', '',
'| 조건 | Opus @1 | 교집합 @1 | Opus @5 | 교집합 @5 | Opus @10 | 교집합 @10 |',
'|---|---:|---:|---:|---:|---:|---:|');
for(const c of Object.keys(ranks)) md.push(`| ${c} | ${[1,5,10].flatMap(k=>[cell(O.table1[c][`@${k}`]),cell(I.table1[c][`@${k}`])]).join(' | ')} |`);
md.push('', 'SS-kw − SF의 hit@10 차이는 Opus 40.38%p → 교집합 42.31%p다. hit@1 차이는 36.54%p → 32.69%p다.', '',
'## 5. 최종 로드', '',
'원 보고서와 같은 세션 단위 적중 지표다. “적중/로드한 관련 태스크”는 관련 스킬이 하나라도 포함된 로드 세션 비율이며, 개별 스킬 precision과 다르다. 로드 세트와 none 여부는 라벨에 따라 바뀌지 않는다. SF는 S-b′ 선택 3회, SS는 저장된 두 load 조건 각 1회다.', '',
'| 조건 | Opus 적중/관련 | 교집합 적중/관련 | Opus 적중/로드한 관련 | 교집합 적중/로드한 관련 | 무관련에서 로드 (양쪽 동일) | expect_none에서 로드 | 평균 로드 수/전체 태스크 |',
'|---|---:|---:|---:|---:|---:|---:|---:|');
for(const c of [...Object.keys(loads),'SF pooled 3 runs']) {const a=O.final_load[c],b=I.final_load[c];md.push(`| ${c} | ${cell(a.hit)} | ${cell(b.hit)} | ${cell(a.hit_over_loaded)} | ${cell(b.hit_over_loaded)} | ${cell(a.irrelevant_loaded)} | ${cell(a.expect_none_loaded)} | ${fmt(a.mean_loaded_all.rate)} |`);}
const mean=(label,metric)=>[1,2,3].reduce((n,i)=>n+out[label].final_load[`SF r${i}`][metric].rate,0)/3;
md.push(`| SF 3회 비율 산술평균 | ${fmt(mean('opus','hit'))} | ${fmt(mean('intersection','hit'))} | ${fmt(mean('opus','hit_over_loaded'))} | ${fmt(mean('intersection','hit_over_loaded'))} | ${fmt(mean('opus','irrelevant_loaded'))} | ${fmt(mean('opus','expect_none_loaded'))} | ${fmt(mean('opus','mean_loaded_all'))} |`, '',
'pooled는 세 번의 분자와 분모를 합친 값이다. 원 보고서의 산술평균도 별도 행으로 제시했다. 세 번 반복한 동일 태스크를 독립 태스크 180개로 해석하지 않는다. 관련 적중 평균에서 SS-load-kw − SF는 Opus **+9.62%p** → 교집합 **+7.05%p**로 줄지만 순서는 유지된다.', '',
'## 6. 보조 민감도: GPT만 관련인 후보까지 반영하면', '',
'교집합은 출처별 비대칭을 양방향으로 시험하지 못한다. 그래서 Opus의 관련 태스크 52개를 고정하고 GPT 단독 라벨도 계산했다. 이는 요청된 주 표를 대체하지 않는 보조 비교이며 무관련/관련 재분류 효과를 배제한다.', '',
'| 검색 조건 | Opus @1/@5/@10 | 교집합 @1/@5/@10 | GPT 단독 @1/@5/@10 |',
'|---|---|---|---|');
for(const c of Object.keys(ranks)) md.push(`| ${c} | ${[O,I,out.gpt_fixed_opus_denominator].map(v=>[1,5,10].map(k=>cell(v.table1[c][`@${k}`])).join(' / ')).join(' | ')} |`);
md.push('', '| 최종 로드 조건 | Opus 적중 | 교집합 적중 | GPT 단독 적중 |', '|---|---:|---:|---:|');
for(const c of ['SF pooled 3 runs','SS-load-kw','SS-load-full']) md.push(`| ${c} | ${[O,I,out.gpt_fixed_opus_denominator].map(v=>cell(v.final_load[c].hit)).join(' | ')} |`);
md.push('', '같은 분모에서 SS-load-kw − SF의 최종 적중 차이는 Opus **+9.62%p**, 교집합 **+7.05%p**, GPT 단독 **−5.77%p**다. 따라서 “교집합에서도 SS가 우세하므로 판정자 선택에 견고하다”는 주장은 이 자료로 뒷받침되지 않는다. 검색 SS-kw @10 우세는 GPT 단독에서도 남지만 격차가 **7.69%p**로 작아진다. 두 판정자 평균이나 교집합을 객관적 정답으로 간주하지 말고, 이 범위의 라벨 민감도를 함께 공개하는 편이 적절하다.', '',
'## 7. 재현과 검증', '',
'실행: `node stage8/scripts/gpt_kappa_8_offline.cjs` (e2e 기준). 내장 fs/path/crypto/assert만 사용한다. `metrics_8.py`나 기존 `gpt_kappa_8.py`는 import 시 실행되는 네트워크 조회·기존 결과 쓰기를 피하기 위해 실행하지 않았다.', '',
'검증: 정확히 60태스크/2,270행, 중복·누락·추가 키 없음, 등급 정수 0–3 및 process boolean, 블라인드 카드와 원 후보 설명 일치, Opus relevant와 pool의 ≥2 일치, 검색 top-10·모든 로드 ID의 채점 풀 포함, 로드 성공 원문과 출처 기록 수 일치, 입력 SHA-256 재확인. 검색 top-10과 최종 로드에서 미채점 ID는 0개다. 순위 밖 미채점 후보를 새로 채점하지 않았다.', '',
'기계 판독 결과: [gpt-kappa-8.json](gpt-kappa-8.json). 분자·분모, 60태스크 목록, 모든 결합 행, 태스크별 출처 불일치, 순위·로드 세트, 입력 해시가 들어 있다.', '',
'| 입력 | SHA-256 |', '|---|---|');
for(const [f,h] of Object.entries(hashes)) md.push(`| ${f} | \`${h}\` |`);
fs.writeFileSync(path.join(base,'stage8/gpt-kappa-8.md'),md.join('\n')+'\n');
