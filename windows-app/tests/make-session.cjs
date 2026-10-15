// Real recorder contract, not a separately invented fixture schema.
const fs = require('node:fs');
const core = require('../../phase2-core.js');
const lesson = core.validateLesson({title:'Work life', intro:'Hey! Let’s talk about work.',outro:'Nice work. See you soon!',phraseRepetitions:2,exampleRepetitions:2,minimumPracticeSeconds:1,bufferSeconds:1,phrases:[{phrase:'I usually work from home.',meaning:'Most days, your home is your office.',example:'I work from home, so let’s meet online.',cue:'How about you? Give it a try.'}]});
const session = {id:'test-session',code:'TEST',createdAt:new Date().toISOString(),source:'browser',lesson,segments:core.segments(lesson).map(s=>({...s,complete:true,mime:'audio/webm',durationSeconds:.2}))};
fs.writeFileSync(process.argv[2],JSON.stringify(core.buildExport(session),null,2));
