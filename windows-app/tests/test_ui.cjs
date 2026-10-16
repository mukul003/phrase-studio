const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');

class Element {
  constructor(){this.value='';this.hidden=false;this.disabled=false;this.files=[];this.children=[];this.events={};this.dataset={};this.classList={toggle(){}};}
  addEventListener(name,fn){this.events[name]=fn;}
  replaceChildren(...nodes){this.children=nodes;}
  add(node){this.children.push(node);}
  append(...nodes){this.children.push(...nodes);}
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));

async function boot({health=true,scriptTitle='<img src=x onerror=alert(1)>',saved=false,pdf=true,pdfMode='phrases'}={}) {
  const elements=new Map();const get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  get('preset').value='master';
  const requests=[];let activeJob=null;let nextTimer;
  const routes=async(url,options={})=>{
    requests.push({url,options});
    let status=200,data;
    if(url==='/api/health')data={ready:health,message:health?'Ready':'Setup needed'};
    else if(url==='/api/settings')data={preset:'master',createPdf:pdf,pdfMode};
    else if(url==='/api/projects'&&options.method==='POST')data={id:'project1'};
    else if(url==='/api/projects')data=saved||requests.some(r=>r.url==='/api/projects'&&r.options.method==='POST')?[{id:'project1',title:scriptTitle,importedAt:'2026-10-15'}]:[];
    else if(url==='/api/projects/project1')data={title:scriptTitle,lesson:{phrases:[{}]},totalDurationSeconds:10,warnings:[],timeline:[{type:'phrase',startSeconds:0,endSeconds:2,text:scriptTitle}]};
    else if(url.endsWith('/render'))data=activeJob={id:'job1',status:'rendering',progress:0,message:'Starting'};
    else if(url.endsWith('/job')){data=activeJob;if(!data)status=204;}
    else if(url.endsWith('/cancel')){activeJob={id:'job1',status:'cancelled',progress:0,message:'Rendering cancelled'};data={};}
    else throw Error('Unexpected route '+url);
    return {ok:true,status,json:async()=>data};
  };
  const storage=new Map(saved?[['phrase-studio-project','project1']]:[]);
  const context={document:{getElementById:get,createElement:()=>new Element()},fetch:routes,Option:function(text,value){this.textContent=text;this.value=value;},localStorage:{getItem:key=>storage.get(key),setItem:(key,value)=>storage.set(key,value)},FormData:class{append(){}},setTimeout:fn=>{nextTimer=fn;return 1;},clearTimeout:()=>{},console};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../wwwroot/studio.js'),'utf8'),context);
  await flush();await flush();
  return {get,requests,tick:async()=>{await nextTimer();await flush();},complete:()=>{activeJob={id:'job1',status:'completed',progress:100,message:'Ready',download:'/video.mp4',pdfDownload:pdf?'/slides.pdf':null};}};
}

test('import one package, display untrusted text safely, generate, play and download',async()=>{
  const app=await boot();app.get('package').files=[{name:'recording.zip'}];
  await app.get('import-form').events.submit({preventDefault(){}});
  assert.equal(app.get('title').textContent,'<img src=x onerror=alert(1)>');
  assert.equal(app.get('project').hidden,false);
  assert.equal(app.get('generate').disabled,false);
  await app.get('generate').events.click();
  assert.equal(app.get('generate').disabled,true);
  assert.equal(app.get('projects').disabled,true);
  app.complete();await app.tick();
  assert.equal(app.get('video').src,'/video.mp4');
  assert.equal(app.get('download').href,'/video.mp4');
  assert.equal(app.get('generate').disabled,false);
});

test('missing dependencies prevent import/generation and explain setup',async()=>{
  const app=await boot({health:false});
  assert.equal(app.get('import-button').disabled,true);
  assert.equal(app.get('generate').disabled,true);
  assert.equal(app.get('notice').textContent,'Setup needed');
});

test('restores a saved project and can cancel a render',async()=>{
  const app=await boot({saved:true});
  assert.equal(app.get('project').hidden,false);
  await app.get('generate').events.click();await app.get('cancel').events.click();await app.tick();
  assert.equal(app.get('cancel').hidden,true);
  assert.equal(app.get('generate').disabled,false);
  assert.equal(app.get('job-message').textContent,'Rendering cancelled');
});

test('whoosh defaults off and the saved selection reaches the renderer',async()=>{
  const app=await boot({saved:true});
  assert.equal(app.get('transition-sound').checked,false);
  app.get('transition-sound').checked=true;
  await app.get('transition-sound').events.change();
  const settings=app.requests.findLast(r=>r.url==='/api/settings'&&r.options.method==='POST');
  assert.equal(JSON.parse(settings.options.body).transitionSound,true);
  await app.get('generate').events.click();
  const render=app.requests.findLast(r=>r.url.endsWith('/render'));
  assert.equal(JSON.parse(render.options.body).transitionSound,true);
  assert.equal(app.get('transition-sound').disabled,true);
});


test('PDF defaults on, downloads beside video and disabled preference reaches render',async()=>{
  const app=await boot({saved:true});
  assert.equal(app.get('create-pdf').checked,true);
  await app.get('generate').events.click();app.complete();await app.tick();
  assert.equal(app.get('download-pdf').hidden,false);
  assert.equal(app.get('download-pdf').href,'/slides.pdf');
  const off=await boot({saved:true,pdf:false});
  assert.equal(off.get('create-pdf').checked,false);
  await off.get('create-pdf').events.change();
  const settings=off.requests.findLast(r=>r.url==='/api/settings'&&r.options.method==='POST');
  assert.equal(JSON.parse(settings.options.body).createPdf,false);
  await off.get('generate').events.click();
  assert.equal(JSON.parse(off.requests.findLast(r=>r.url.endsWith('/render')).options.body).createPdf,false);
  off.complete();await off.tick();assert.equal(off.get('download-pdf').hidden,true);
});


test('PDF content defaults to phrases, remembers all sections and locks when off',async()=>{
  const app=await boot({saved:true});
  assert.equal(app.get('pdf-mode').value,'phrases');
  app.get('pdf-mode').value='all';await app.get('pdf-mode').events.change();
  assert.equal(JSON.parse(app.requests.findLast(r=>r.url==='/api/settings'&&r.options.method==='POST').options.body).pdfMode,'all');
  await app.get('generate').events.click();
  assert.equal(JSON.parse(app.requests.findLast(r=>r.url.endsWith('/render')).options.body).pdfMode,'all');
  assert.equal(app.get('pdf-mode').disabled,true);
  const restored=await boot({saved:true,pdfMode:'all'});assert.equal(restored.get('pdf-mode').value,'all');
  restored.get('create-pdf').checked=false;await restored.get('create-pdf').events.change();
  assert.equal(restored.get('pdf-mode').disabled,true);
});
