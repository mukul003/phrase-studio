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

async function boot({health=true,scriptTitle='<img src=x onerror=alert(1)>',saved=false}={}) {
  const elements=new Map();const get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  get('preset').value='master';
  const requests=[];let activeJob=null;let nextTimer;
  const routes=async(url,options={})=>{
    requests.push({url,options});
    let status=200,data;
    if(url==='/api/health')data={ready:health,message:health?'Ready':'Setup needed'};
    else if(url==='/api/settings')data={preset:'master'};
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
  return {get,requests,tick:async()=>{await nextTimer();await flush();},complete:()=>{activeJob={id:'job1',status:'completed',progress:100,message:'Ready',download:'/video.mp4'};}};
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
