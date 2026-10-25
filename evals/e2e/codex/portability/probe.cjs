const fs = require('fs');
const cp = require('child_process');
const readline = require('readline');
const dir = '/tmp/skillfetch-codex-portability';
const env = {PATH: process.env.PATH, HOME: process.env.HOME, TMPDIR: process.env.TMPDIR, CODEX_HOME: dir+'/home'};
const args = ['-f', dir+'/network-deny.sb', '/opt/homebrew/bin/codex', 'app-server', '--stdio'];
fs.writeFileSync(dir+'/launch.json',JSON.stringify({command:'/usr/bin/sandbox-exec',args,env:{CODEX_HOME:env.CODEX_HOME},cwd:dir+'/work'},null,2));
const transcript=fs.createWriteStream(dir+'/transcript.jsonl');
const stderr=fs.openSync(dir+'/stderr.log','w');
const child=cp.spawn('/usr/bin/sandbox-exec',args,{env,cwd:dir+'/work',stdio:['pipe','pipe',stderr]});
let id=0;
const pending=new Map();
const record=(direction,message)=>transcript.write(JSON.stringify({at:new Date().toISOString(),direction,message})+'\n');
readline.createInterface({input:child.stdout}).on('line',line=>{
 let msg;try{msg=JSON.parse(line)}catch{record('invalid',line);return;}
 record('receive',msg);
 if(msg.id!==undefined && pending.has(msg.id)) {let p=pending.get(msg.id);pending.delete(msg.id);p(msg);}
 else if(msg.id!==undefined && msg.method) {let response={jsonrpc:'2.0',id:msg.id,error:{code:-32601,message:'No interactive approvals in offline probe'}};record('send',response);child.stdin.write(JSON.stringify(response)+'\n');}
});
function send(method,params,request=true) {
 const msg={jsonrpc:'2.0',method,params};
 if(request)msg.id=++id;
 record('send',msg);
 return new Promise((resolve,reject)=>{if(request)pending.set(msg.id,resolve);child.stdin.write(JSON.stringify(msg)+'\n');if(!request)resolve({});setTimeout(()=>{if(pending.has(msg.id)){pending.delete(msg.id);reject(new Error('timeout '+method));}},45000).unref();});
}
(async()=>{
 try{
  const initialize=await send('initialize',{clientInfo:{name:'skillfetch_offline_portability_probe',title:'skillfetch offline portability probe',version:'1.0'},capabilities:{experimentalApi:true}});
  console.log('initialize',JSON.stringify(initialize));
  if(initialize.error)throw new Error(JSON.stringify(initialize.error));
  await send('initialized',{},false);
  const start=await send('thread/start',{cwd:dir+'/work',ephemeral:true,approvalPolicy:'never',sandbox:'read-only'});
  fs.writeFileSync(dir+'/thread-start.json',JSON.stringify(start,null,2));
  if(start.error)throw new Error(JSON.stringify(start.error));
  const threadId=start.result.thread.id;
  console.log('threadId',threadId);
  const status=await send('mcpServerStatus/list',{threadId,serverName:'skillfetch'});
  fs.writeFileSync(dir+'/mcp-status.json',JSON.stringify(status,null,2));
  console.log('status',JSON.stringify(status));
  const arguments={queries:['Add keyboard navigation and accessible focus states to a React settings form.','React and TypeScript.'],k:5};
  const result=await send('mcpServer/tool/call',{threadId,server:'skillfetch',tool:'search_skills',arguments});
  fs.writeFileSync(dir+'/search-result.json',JSON.stringify(result,null,2));
  console.log('search',JSON.stringify(result));
  if(result.error||result.result?.isError)process.exitCode=1;
 }catch(e){console.error(String(e));process.exitCode=1;}
 finally{child.stdin.end();child.kill('SIGTERM');transcript.end();setTimeout(()=>child.kill('SIGKILL'),2000).unref();}
})();
