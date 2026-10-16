'use strict';
const $ = id => document.getElementById(id);
let projectId = '', jobId = '', timer, ready = false, busy = false;
function notice(text, error = false) { $('notice').textContent = text; $('notice').classList.toggle('error', error); }
function controls() { $('generate').disabled = !ready || busy || !projectId; $('import-button').disabled = !ready || busy; $('projects').disabled = busy; $('preset').disabled = busy; $('transition-sound').disabled = busy; }
async function api(url, options = {}) {
  const response = await fetch(url, {...options, headers: {'X-Phrase-Studio':'local', ...options.headers}});
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) throw Error(data.error || `Request failed (${response.status})`);
  return data;
}
async function projects(selected = '') {
  const list = await api('/api/projects');
  $('projects').replaceChildren(new Option('Choose a project', ''));
  list.sort((a,b) => b.importedAt.localeCompare(a.importedAt)).forEach(p => $('projects').add(new Option(p.title, p.id)));
  if (list.some(p => p.id === selected)) { $('projects').value = selected; await load(selected); }
}
async function load(id) {
  clearTimeout(timer); projectId = id; jobId = ''; $('result').hidden = true; $('job').hidden = true;
  $('project').hidden = !id; $('empty').hidden = !!id;
  if (!id) { controls(); return; }
  localStorage.setItem('phrase-studio-project', id);
  const doc = await api('/api/projects/' + id);
  $('title').textContent = doc.title;
  $('summary').textContent = `${doc.lesson.phrases.length} phrases · ${Math.ceil(doc.totalDurationSeconds)} seconds · intro/outro kept · one viewer turn per phrase`;
  $('warnings').replaceChildren(...doc.warnings.map(w => { const li=document.createElement('li');li.textContent=w;return li; }));
  const phraseById = new Map(doc.lesson.phrases.map(p => [p.id,p.phrase]));
  $('timeline').replaceChildren(...doc.timeline.map(s => {
    const li=document.createElement('li');li.className='section';
    const label=document.createElement('span'); label.textContent=`${s.type.replaceAll('-',' ')} · ${(s.endSeconds-s.startSeconds).toFixed(1)}s`;
    const text=document.createElement('p'); text.textContent=s.displayText ?? phraseById.get(s.phraseId) ?? s.text; li.append(label,text);return li;
  }));
  const job = await api('/api/projects/' + id + '/job');
  if (job) showJob(job); else { busy=false;controls(); }
}
function showJob(job) {
  jobId=job.id; busy=job.status==='rendering'; $('job').hidden=false;
  $('progress').value=job.progress; $('job-message').textContent=job.message;
  $('cancel').hidden=!busy;controls();
  if (job.status==='completed') {
    $('result').hidden=false; $('video').dataset.ready='false'; $('video').src=job.download; $('download').href=job.download;
    notice('Your video is ready. Play it here, then save it.');
  } else if (job.status==='failed' || job.status==='cancelled') notice(job.message, job.status==='failed');
  if (busy) timer=setTimeout(poll,1200);
}
async function poll() {
  try { const job=await api('/api/projects/'+projectId+'/job');if(job)showJob(job); }
  catch(error) { notice('Connection lost. Keep the app open; reconnecting…',true);timer=setTimeout(poll,3000); }
}
$('video').addEventListener('loadedmetadata', () => { $('video').dataset.ready='true'; });
$('video').addEventListener('error', () => { notice('Video preview unavailable in this browser. Save the video to play it locally.', true); });
$('import-form').addEventListener('submit', async e => {
  e.preventDefault();const file=$('package').files[0];if(!file)return;
  busy=true;controls();notice('Importing and checking your recordings…');
  try { const body=new FormData();body.append('package',file);const result=await api('/api/projects',{method:'POST',body});await projects(result.id);notice('Recording checked. You’re ready to generate.'); }
  catch(error){notice(error.message,true);}
  finally{busy=false;controls();}
});
$('projects').addEventListener('change',()=>load($('projects').value).catch(e=>notice(e.message,true)));
function renderSettings() { return {preset:$('preset').value, transitionSound:$('transition-sound').checked === true}; }
function saveSettings() { return api('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(renderSettings())}).catch(e=>notice(e.message,true)); }
$('preset').addEventListener('change',saveSettings);
$('transition-sound').addEventListener('change',saveSettings);
$('generate').addEventListener('click',async()=>{
  busy=true;controls();$('result').hidden=true;
  try{const job=await api('/api/projects/'+projectId+'/render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(renderSettings())});notice('Creating your video. You can leave this window open.');showJob(job);}
  catch(error){busy=false;controls();notice(error.message,true);}
});
$('cancel').addEventListener('click',async()=>{try{await api('/api/jobs/'+jobId+'/cancel',{method:'POST'});}catch(error){notice(error.message,true);}});
(async()=>{try{
  const [health,settings]=await Promise.all([api('/api/health'),api('/api/settings')]);
  ready=health.ready;notice(health.message,!ready);$('preset').value=settings.preset; $('transition-sound').checked=settings.transitionSound === true;
  await projects(localStorage.getItem('phrase-studio-project')||'');controls();
}catch(error){notice(error.message,true);controls();}})();
