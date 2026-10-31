const $ = id => document.getElementById(id);
let configs = [], currentRun = null;
const api = async (path, method='GET', body=null) => {
  const options = {method, headers:{}};
  if (body !== null) { options.headers['Content-Type']='application/json'; options.headers['X-Chaos-Local']='1'; options.body=JSON.stringify(body); }
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
};
const notice = (message, error=false) => { $('notice').textContent=message; $('notice').classList.toggle('error',error); };
const node = (tag, className='', text='') => { const n=document.createElement(tag); n.className=className; n.textContent=text; return n; };

async function loadConfigs() {
  configs=(await api('/api/configs')).configs;
  const chosen=$('config-select').value;
  $('config-select').replaceChildren();
  configs.forEach(c => {const o=node('option','',`${c.name}${c.valid?'':' · invalid'}`);o.value=c.id;$('config-select').append(o);});
  if (configs.some(c=>c.id===chosen)) $('config-select').value=chosen;
  showConfig();
}
async function loadProjects() {
  const projects=(await api('/api/projects')).projects;
  const list=$('project-list');list.replaceChildren();
  if (!projects.length) {list.append(node('p','empty','No app copies imported yet.'));return;}
  projects.forEach(project=>{
    const item=node('div','project-item');
    item.append(node('strong','',project.name));
    item.append(node('p','muted',`${project.id} · ${project.file_count} files · ${(project.expanded_bytes/1048576).toFixed(2)} MiB · ${project.config_ids.length?`${project.config_ids.length} saved config`:'configuration needed'}`));
    const controls=node('div','button-row');
    const configure=node('button','secondary','Configure');configure.type='button';
    configure.addEventListener('click',()=>guarded(()=>configureProject(project.id))());
    const download=node('button','secondary','Download bundle');download.type='button';
    download.addEventListener('click',()=>guarded(()=>downloadProject(project.id))());
    controls.append(configure,download);item.append(controls);list.append(item);
  });
}
async function configureProject(id) {
  const project=await api(`/api/projects/${id}`);
  if (project.config_ids.length) {
    await loadConfigs();$('config-select').value=project.config_ids[0];showConfig();
    notice(`Selected ${project.config_ids[0]}. You can run this imported copy.`);
    return;
  }
  const template=(await api('/api/configs/example')).config;
  template.name=`${project.name} check`;
  template.cwd=project.path;
  template.source_paths=project.files.filter(f=>f.path.endsWith('.py')).slice(0,50).map(f=>`${project.path}/${f.path}`);
  $('new-id').value=id;
  $('config-editor').value=JSON.stringify(template,null,2);
  $('config-editor').focus();
  notice('App copy selected. Set the target and checker commands, input grammar, controls, and source files, then save.');
}
async function importProject() {
  const file=$('project-file').files[0];
  if (!file) throw new Error('Choose a ZIP file.');
  if (file.size>100*1024*1024) throw new Error('ZIP is larger than 100 MiB.');
  const id=$('project-id').value.trim();
  const name=$('project-name').value.trim()||id;
  const response=await fetch('/api/projects/import',{method:'POST',body:file,headers:{
    'Content-Type':'application/zip','X-Chaos-Local':'1','X-Chaos-Project-Id':id,
    'X-Chaos-Project-Name':encodeURIComponent(name)}});
  const result=await response.json();
  if (!response.ok) throw new Error(result.error||`HTTP ${response.status}`);
  await loadProjects();await loadConfigs();
  if (result.config_ids.length) {$('config-select').value=result.config_ids[0];showConfig();}
  $('project-file').value='';
  notice(`Imported ${name} as a local copy. ${result.config_ids.length?'Runnable configuration created.':'Add a target/checker configuration to run it.'}`);
}
async function downloadProject(id) {
  const response=await fetch(`/api/projects/${id}/export`,{headers:{'X-Chaos-Local':'1'}});
  if (!response.ok) {const error=await response.json();throw new Error(error.error||`HTTP ${response.status}`);}
  const blob=await response.blob();const url=URL.createObjectURL(blob);
  const anchor=document.createElement('a');anchor.href=url;anchor.download=`${id}.chaos.zip`;
  document.body.append(anchor);anchor.click();anchor.remove();
  setTimeout(()=>URL.revokeObjectURL(url),30000);
  notice(`Downloaded ${id}.chaos.zip.`);
}
function showConfig() {
  const c=configs.find(x=>x.id===$('config-select').value);
  $('config-meta').textContent=c ? `${c.id} · ${c.path}${c.valid?'':` · ${c.error}`}` : '';
  $('run-button').disabled=!c || !c.valid;
}
async function copyConfig() {
  const current=await api(`/api/configs/${encodeURIComponent($('config-select').value)}`);
  const c=current.config;
  const examplePath=configs.find(x=>x.id==='example')?.path;
  const base=current.id==='example' && examplePath ? examplePath.slice(0,examplePath.lastIndexOf('/')) : null;
  if (base) {
    c.cwd=base;
    c.source_paths=c.source_paths.map(p=>p.startsWith('/')?p:`${base}/${p}`);
  }
  $('config-editor').value=JSON.stringify(c,null,2);
  $('new-id').value=current.id==='example'?'my-project-check':`${current.id}-copy`;
  $('config-editor').focus();
  notice('Config copied. Set its project paths, commands, input grammar, and controls before saving.');
}
async function saveConfig() {
  const id=$('new-id').value.trim();
  const config=JSON.parse($('config-editor').value);
  const saved=await api('/api/configs','POST',{id,config});
  await loadConfigs();$('config-select').value=saved.id;showConfig();
  notice(`Saved ${saved.id}.`);
}
async function startRun() {
  const run=await api('/api/runs','POST',{config_id:$('config-select').value});
  currentRun=run.id; await showRun(run.id); await loadRuns(); notice(`Started run ${run.id}.`);
}
async function loadRuns() {
  const runs=(await api('/api/runs')).runs;
  const container=$('run-list');container.replaceChildren();
  if (!runs.length) {container.append(node('p','empty','No runs yet.'));return;}
  runs.forEach(run=>{
    const button=node('button','run-item');button.type='button';
    button.append(node('span','',`${run.config_id} · ${run.id.slice(0,8)}`),node('span','state '+run.state,run.state));
    button.addEventListener('click',()=>showRun(run.id).catch(e=>notice(e.message,true)));
    container.append(button);
  });
}
async function showRun(id) {
  const run=await api(`/api/runs/${id}`);currentRun=id;
  $('current-empty').hidden=true;$('current-detail').hidden=false;
  $('run-state').textContent=run.state;$('run-state').className='state '+run.state;
  $('run-id').textContent=run.id;
  $('run-description').textContent=`${run.config_id} · started ${new Date(run.started_at).toLocaleString()}${run.finished_at?` · finished ${new Date(run.finished_at).toLocaleString()}`:''}`;
  $('cancel-button').hidden=!['starting','running'].includes(run.state);
  if (run.state==='succeeded') {const result=await api(`/api/runs/${id}/receipt`);renderResults(result);}
  else {$('results').hidden=true;$('results-empty').hidden=false;
    if (run.state==='failed') {
      const details=await api(`/api/runs/${id}/log`);
      $('results-empty').textContent=`Run failed. ${details.log || run.error || 'No diagnostic log was recorded.'}`;
    } else $('results-empty').textContent='The run is still working. Results appear here when it finishes.';}
}
function renderResults(result) {
  $('results').hidden=false;$('results-empty').hidden=true;
  $('score-off').textContent=result.scores.off;$('score-on').textContent=result.scores.on;
  const witnesses=Object.entries(result.arms).flatMap(([arm,rows])=>rows.filter(r=>r.witness).map(r=>({arm,...r})));
  $('witness-count').textContent=witnesses.length;
  const gates=$('gates');gates.replaceChildren();
  Object.entries(result.gates).forEach(([name,value])=>{
    const item=node('div','gate '+(value==='FAILED'?'failed':''));
    item.append(node('span','',name.replaceAll('_',' ')),node('strong','',value));gates.append(item);
  });
  const list=$('witnesses');list.replaceChildren();
  if (!witnesses.length) {list.append(node('p','empty','No verified findings in this run.'));return;}
  witnesses.forEach(w=>{const item=node('div','witness');
    item.append(node('strong','',`${w.arm.toUpperCase()} · seed ${w.seed} · call ${w.first_hit}`));
    item.append(node('pre','',JSON.stringify(w.witness.request,null,2)));list.append(item);});
}
async function cancelRun() {if (!currentRun)return;await api(`/api/runs/${currentRun}/cancel`,'POST',{});await showRun(currentRun);await loadRuns();notice('Run stopped.');}
async function refresh() {await loadRuns();if(currentRun)await showRun(currentRun);}
const guarded=fn=>async()=>{try{await fn();}catch(e){notice(e.message,true);}};
$('config-select').addEventListener('change',showConfig);
$('run-button').addEventListener('click',guarded(startRun));
$('copy-button').addEventListener('click',guarded(copyConfig));
$('save-button').addEventListener('click',guarded(saveConfig));
$('refresh-button').addEventListener('click',guarded(refresh));
$('cancel-button').addEventListener('click',guarded(cancelRun));
$('import-button').addEventListener('click',guarded(importProject));
guarded(async()=>{await loadConfigs();await loadProjects();await loadRuns();})().then(()=>{});
setInterval(()=>{if(currentRun)showRun(currentRun).catch(()=>{});loadRuns().catch(()=>{});},1500);
