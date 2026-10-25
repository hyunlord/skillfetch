'use strict';
const fs = require('node:fs');
const path = require('node:path');
const cp = require('node:child_process');
const os = require('node:os');
const { AppServer, awaitMcpConnected, isolatedEnvironment, verifyLogin } = require('./codex-e2e-2-runner.cjs');
const base = __dirname;
const prep = path.join(base, 'codex-e2e-2-preparation');
const dir = path.join(base, 'codex-e2e-2-smoke');
const repo = path.join(base, 'repos/fastapi');
const ref = '2b38acb4586092ef0318bc6a8ab36436ba8fc09a';
const auth = '<home>/Library/Application Support/orca/codex-accounts/54be5844-95fd-4c46-925c-75327ccd186a/home/auth.json';
const codex = '/opt/homebrew/bin/codex';
function ensure(ok, message) { if (!ok) throw Error(message); }
function json(name, value) { fs.writeFileSync(path.join(dir, name), JSON.stringify(value, null, 2) + '\n'); }
function command(exe, args, options = {}) {
  const r = cp.spawnSync(exe, args, {encoding:'utf8',timeout:120000,maxBuffer:16*1024*1024,...options});
  ensure(r.status === 0, `${exe} failed: ${r.error?.message || r.stderr}`);
  return r.stdout;
}
async function main() {
  ensure(!fs.existsSync(dir), 'Smoke directory exists; refusing duplicate run');
  fs.mkdirSync(dir, {mode:0o700});
  const owned = fs.mkdtempSync(path.join(os.tmpdir(), 'skillfetch-e2e2-smoke-'));
  const cwd = path.join(owned, 'fastapi');
  const home = path.join(dir, 'home');
  const ch = path.join(home, '.codex');
  const tmp = path.join(dir, 'tmp');
  const report = {cohort:false,purpose:'model-mediated MCP approval preflight',started_at:new Date().toISOString(),worktree:cwd};
  let rpc, timer, added=false;
  let complete, fail;
  const done = new Promise((resolve,reject)=>{complete=resolve;fail=reject;});done.catch(()=>{});
  try {
    command('git',['-C',repo,'worktree','add','--detach',cwd,ref]);added=true;
    fs.mkdirSync(ch,{recursive:true,mode:0o700});fs.mkdirSync(tmp,{mode:0o700});
    fs.copyFileSync(path.join(prep,'AGENTS.md'),path.join(cwd,'AGENTS.md'));
    fs.copyFileSync(path.join(prep,'config-template.toml'),path.join(ch,'config.toml'));
    fs.copyFileSync(path.join(prep,'cloud-skills.json'),path.join(ch,'cloud-skills.json'));
    fs.symlinkSync(auth,path.join(ch,'auth.json'));
    const env = isolatedEnvironment(home,ch,tmp);
    report.login=verifyLogin(dir,cwd,env);
    const mcp = command(codex,['mcp','get','skillfetch'],{cwd,env});
    fs.writeFileSync(path.join(dir,'mcp-get.txt'),mcp);
    ensure(mcp.includes('default_tools_approval_mode: approve'),'MCP approve setting absent');
    fs.writeFileSync(path.join(dir,'startup-config.txt'),command(codex,['app-server','--strict-config','--print-startup-config'],{cwd,env}));
    const calls = new Map();
    rpc = new AppServer(dir,cwd,env,path.join(ch,'cloud-skills.json'),(message)=>{
      if(message.method==='runner/failure')fail(Error(message.params.message));
      if(message.method==='item/completed' && message.params?.item?.type==='mcpToolCall'){
        calls.set(message.params.item.id,message.params.item);
        json('mcp-completed.json',[...calls.values()]);
      }
      if(message.method==='turn/completed')complete(message.params.turn);
    });
    timer=setTimeout(()=>fail(Error('Smoke timeout 600 seconds')),600000);
    await rpc.request('initialize',{clientInfo:{name:'skillfetch_approval_smoke',version:'1.0'},capabilities:{experimentalApi:true}});
    rpc.send({jsonrpc:'2.0',method:'initialized',params:{}});
    const account = await rpc.request('account/read',{refreshToken:false});
    json('account-read.json',account);
    ensure(account.result?.account?.type==='chatgpt' && account.result.account.planType==='pro','Expected ChatGPT Pro');
    const start=await rpc.request('thread/start',{cwd,ephemeral:true,approvalPolicy:'never',sandbox:'workspace-write',experimentalRawEvents:true,model:'gpt-6-astra'});
    json('thread-start.json',start);
    ensure(start.result.model==='gpt-6-astra' && start.result.reasoningEffort==='medium','Model mismatch');
    ensure(start.result.approvalPolicy==='never' && start.result.sandbox?.type==='workspaceWrite' && start.result.sandbox.networkAccess===false,'Policy mismatch');
    await awaitMcpConnected(rpc,start.result.thread.id,dir);
    const prompt='This is a routing connection preflight, not an implementation task. Use only skillfetch MCP tools: call profile_repo for the current repository, call search_skills with four queries about FastAPI endpoint testing including this entire request verbatim as query four, choose one returned skill, call resolve_set, then call load_skills with the resolved IDs. Do not edit files or run shell commands. Finish with the loaded skill ID or the exact failure.';
    fs.writeFileSync(path.join(dir,'prompt.txt'),prompt);
    await rpc.request('turn/start',{threadId:start.result.thread.id,input:[{type:'text',text:prompt}]});
    report.turn=await done;
    report.calls=[...calls.values()].map(c=>({id:c.id,server:c.server,tool:c.tool,status:c.status,error:c.error,has_result:c.result!=null}));
    ensure(report.turn.status==='completed','Smoke turn incomplete');
    for(const tool of ['profile_repo','search_skills','resolve_set','load_skills'])ensure([...calls.values()].some(c=>c.server==='skillfetch'&&c.tool===tool&&c.status==='completed'&&c.result!=null&&!c.error&&!c.result.isError),`No real successful ${tool} result`);
    report.status='PASS';
  } catch(error) { report.status='FAIL';report.error=error.message;process.exitCode=1; }
  finally {
    clearTimeout(timer);if(rpc)await rpc.close();
    fs.rmSync(path.join(ch,'auth.json'),{force:true});
    if(added)command('git',['-C',repo,'worktree','remove','--force',cwd]);
    fs.rmdirSync(owned);report.cleanup='DONE';report.finished_at=new Date().toISOString();json('verification.json',report);
    console.log(JSON.stringify(report));
  }
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
