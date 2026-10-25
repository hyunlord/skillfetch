'use strict';
const fs=require('node:fs');
const path=require('node:path');
const root=path.join(__dirname,'codex-e2e-3-runs/20261024-full-router-14d2020');
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const parent=read(path.join(root,'manifest.json'));
const output={at:new Date().toISOString(),status:parent.status,replicates:[]};
for(const rep of ['r1','r2','r3']){
  const file=path.join(root,rep,'manifest.json');
  if(!fs.existsSync(file)){output.replicates.push({id:rep,status:'NOT_STARTED'});continue;}
  const m=read(file);
  const row={id:rep,status:m.status,states:{},cleanup_done:0,submitted:0,called_sessions:0,search_result_sessions:0,load_result_sessions:0,mcp_protocol_errors:0,approval_denials:0,active:[]};
  for(const task of m.tasks){
    row.states[task.status]=(row.states[task.status]||0)+1;
    row.cleanup_done+=task.cleanup==='DONE';
    row.submitted+=task.turn_start_requested===true;
    if(task.status==='RUNNING')row.active.push(task.id);
    const events=path.join(root,rep,'tasks',task.id,'mcp-events.jsonl');
    if(!fs.existsSync(events))continue;
    const calls=new Map();
    for(const line of fs.readFileSync(events,'utf8').split('\n')){
      if(!line)continue;
      let event;try{event=JSON.parse(line);}catch{continue;}
      if(event.message?.method==='item/completed')calls.set(event.message.params.item.id,event.message.params.item);
    }
    const values=[...calls.values()];
    row.called_sessions+=values.length>0;
    row.search_result_sessions+=values.some(c=>c.tool==='search_skills'&&c.result&&!c.error);
    row.load_result_sessions+=values.some(c=>c.tool==='load_skills'&&c.result&&!c.error);
    row.mcp_protocol_errors+=values.filter(c=>c.error||c.result?.isError).length;
    row.approval_denials+=values.filter(c=>c.error?.message?.includes('approval policy')).length;
  }
  output.replicates.push(row);
}
console.log(JSON.stringify(output,null,2));
