(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.Phase2=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const TYPES=['phrase','meaning','example','cue'];
function validateLesson(input){
 if(!input||typeof input!=='object')throw Error('Choose a valid lesson JSON.');
 const title=String(input.title||'').trim();if(!title)throw Error('Add a lesson title.');
 if(!Array.isArray(input.phrases)||!input.phrases.length||input.phrases.length>100)throw Error('Add between 1 and 100 phrases.');
 const phrases=input.phrases.map((p,i)=>{let out={id:'p'+String(i+1).padStart(4,'0')};for(const t of TYPES){out[t]=String(p[t]??(t==='phrase'?p.text:'')??'').trim();if(!out[t])throw Error('Phrase '+(i+1)+': add '+t+'.');if(out[t].length>5000)throw Error('Phrase '+(i+1)+': '+t+' is too long.');}const v=p.practiceSeconds;if(v!==''&&v!==null&&v!==undefined){out.practiceSeconds=Number(v);if(!Number.isFinite(out.practiceSeconds)||out.practiceSeconds<1||out.practiceSeconds>120)throw Error('Practice time must be between 1 and 120 seconds.');}return out;});
 return {title,intro:String(input.intro||'').trim(),outro:String(input.outro||'').trim(),bufferSeconds:finite(input.bufferSeconds,1,0,10),minimumPracticeSeconds:finite(input.minimumPracticeSeconds,3,1,30),phrases};
}
function finite(v,fallback,min,max){if(v===undefined||v===null||v==='')return fallback;const n=Number(v);if(!Number.isFinite(n)||n<min||n>max)throw Error('Timing setting is outside its allowed range.');return n;}
function segments(lesson){let out=[];if(lesson.intro)out.push({id:'intro',type:'intro',text:lesson.intro,phraseId:null});for(const p of lesson.phrases)for(const t of TYPES)out.push({id:p.id+'-'+t,type:t,text:p[t],phraseId:p.id});if(lesson.outro)out.push({id:'outro',type:'outro',text:lesson.outro,phraseId:null});return out;}
function practiceTime(lesson,p,recordings){
 if(p.practiceSeconds!==undefined)return {seconds:p.practiceSeconds,basis:'manual'};
 const rec=recordings.find(r=>r.phraseId===p.id&&r.type==='phrase');
 const duration=Number(rec?.durationSeconds);
 const recorded=rec?.complete===true&&Number.isFinite(duration)&&duration>0;
 const estimate=recorded?duration:p.phrase.split(/\s+/).filter(Boolean).length/2;
 return {seconds:Math.round(Math.max(lesson.minimumPracticeSeconds,estimate+lesson.bufferSeconds)*1000)/1000,basis:recorded?'phrase-only-duration':'word-count-estimate'};
}
function buildExport(session){
 const ready=session.segments.every(s=>s.complete&&Number.isFinite(s.durationSeconds)&&s.durationSeconds>0);
 let at=0;const timeline=[];
 for(const s of session.segments){if(!s.complete)continue;const d=s.durationSeconds;timeline.push({id:s.id,type:s.type,phraseId:s.phraseId,text:s.text,startSeconds:round(at),endSeconds:round(at+d),durationSeconds:d,source:session.source==='browser'?{file:'clips/'+s.id+'.'+extension(s.mime)}:{startSeconds:s.sourceStartSeconds,endSeconds:s.sourceEndSeconds,relativeTo:'session-timing-clock'}});at+=d;if(s.type==='cue'){const p=session.lesson.phrases.find(p=>p.id===s.phraseId),time=practiceTime(session.lesson,p,session.segments);timeline.push({id:p.id+'-viewer-turn',type:'viewer-turn',phraseId:p.id,text:p.phrase,startSeconds:round(at),endSeconds:round(at+time.seconds),durationSeconds:time.seconds,durationBasis:time.basis,audio:'silence',repetitions:1,visual:{label:'YOUR TURN — SAY IT ALOUD!',indicator:'shrinking-horizontal-line',showNumbers:false,showTrack:false,ticking:false}});at+=time.seconds;}}
 return {schemaVersion:3,mode:'learn-and-practise',sessionId:session.id,sessionCode:session.code,title:session.lesson.title,createdAt:session.createdAt,exportedAt:new Date().toISOString(),narratorRepetitions:1,viewerRepetitions:1,source:session.source,renderReady:ready,requiresSourceAudio:session.source==='voice-memos',alignment:session.source==='voice-memos'?{syncMarker:session.syncMarker,events:session.events,reviewRequired:true,note:'Align the spoken marker and each timing run to the external recording. Enhanced audio may change timing.'}:null,lesson:session.lesson,segments:session.segments.map(({audio,...s})=>s),timeline,totalDurationSeconds:round(at),incompleteSegmentIds:session.segments.filter(s=>!s.complete).map(s=>s.id),renderRules:{wordHighlighting:false,footageBackground:false,musicOptional:true}};
}
const round=n=>Math.round(n*1000)/1000;
function extension(mime){return /webm/.test(mime||'')?'webm':/ogg/.test(mime||'')?'ogg':'m4a';}
// Store-only ZIP; UTF-8 filenames and CRC32, no third-party dependency.
async function zip(files){const enc=new TextEncoder(),u16=v=>[v&255,v>>>8&255],u32=v=>[v&255,v>>>8&255,v>>>16&255,v>>>24&255];let parts=[],central=[],offset=0;for(const f of files){const name=enc.encode(f.name),data=f.data instanceof Blob?new Uint8Array(await f.data.arrayBuffer()):enc.encode(f.data);let crc=0xffffffff;for(const b of data){crc^=b;for(let j=0;j<8;j++)crc=(crc&1)?0xedb88320^(crc>>>1):crc>>>1;}crc=(crc^0xffffffff)>>>0;const head=new Uint8Array([80,75,3,4,20,0,0,8,0,0,0,0,0,0,...u32(crc),...u32(data.length),...u32(data.length),...u16(name.length),0,0]);parts.push(head,name,data);central.push(new Uint8Array([80,75,1,2,20,0,20,0,0,8,0,0,0,0,0,0,...u32(crc),...u32(data.length),...u32(data.length),...u16(name.length),0,0,0,0,0,0,0,0,0,0,0,0,...u32(offset)]),name);offset+=head.length+name.length+data.length;}const centralSize=central.reduce((s,p)=>s+p.length,0);return new Blob([...parts,...central,new Uint8Array([80,75,5,6,0,0,0,0,...u16(files.length),...u16(files.length),...u32(centralSize),...u32(offset),0,0])],{type:'application/zip'});}
return {validateLesson,segments,practiceTime,buildExport,extension,zip};
});
