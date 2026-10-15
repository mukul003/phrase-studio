# Phase 2 — Learn & Practise

Open `phase2.html` from either Phase 1 page. The Work Life lesson is preloaded, including the conversational introduction and outro. All words are editable. Saved Phase 1 sessions remain in their existing storage and formats.

## Paste a generated response

Paste the entire generated lesson into the box at the top, then Parse & fill lesson to review, or Start recording this lesson to parse and create the session directly. No field-by-field entry or JSON file is required. The detailed editor is collapsed by default.

The parser accepts labeled plain text, common numbered Markdown, sentence/summary/example tables, JSON lessons and an exported session's lesson object. Intro/Introduction, Sentence/Phrase, Summary/Meaning/Explanation, Example and Outro/Conclusion are recognized. Multiline fields are preserved. Missing cues are filled automatically. Missing summaries/examples produce a specific error and do not overwrite the current editor. Unlabeled monologues cannot be segmented reliably; use the built-in generation prompt to get a consistent format.

Open “Get a reusable generation prompt”, copy it, replace [TOPIC] and ask for the response. A “Try sample format” button demonstrates the format. The complete prompt and sample are served from phase2-import.js.

## Repetitions

“Say each phrase” and “Say each example” each support once or twice. Individual overrides are under each item's optional repetition settings, or paste Repeat phrase: 2 / Repeat example: 2. Existing sessions keep their original structure. Set repetitions before creating a new recording session.

Every repetition gets a separate recording/timing section with a visible repetition counter. Read that section once and tap Next to capture the next repetition. Meaning, cue, intro and outro remain single sections. Viewer turns still occur exactly once after the cue. The viewer timer uses the average duration of completed individual phrase repetitions plus the buffer/minimum, never the sum of the two takes or any example duration.

## Recording

Choose browser microphone or Apple Voice Memos timing companion before creating a session. Read every section **once**. The sequence is intro, then phrase / meaning / example / cue for each phrase, then outro. The silent viewer turns are generated from metadata; do not record them.

Browser: Record section, then Save & next. Next immediately starts recording the next section. Stop & save ends recording without advancing; use Next section to navigate afterward. Any section can be revisited and retaken. Complete all sections to enable the audio ZIP and full audio/timer preview. The microphone input meter flags clipping.

Voice Memos: Start Apple's recording, return to the page, Start timing, speak the shown session marker, then Begin section. Tap Save & next at each boundary. After the final section, stop Voice Memos separately. Download the JSON and retain the matching M4A. After a stopped/reloaded timing session, speak a fresh marker to anchor the new timing run. Each run is recorded in events. The source audio needs manual marker alignment in the video generator, especially after audio enhancement.

## Interrupted recording: pause and restart

The recording controls include Pause and Restart current section. Completed sections and existing successful takes stay saved.

Browser microphone:
- Pause recording pauses MediaRecorder and freezes the section clock. No paused time is added to the fallback duration; native media capture omits paused audio.
- Resume recording continues the same take. Save & next is disabled while paused.
- Restart current section discards the current unsaved take, resets its clock and immediately starts a clean recording of the same section/repetition. It works while recording or paused, and for retaking a saved section.
- A previous successful take is retained until its replacement has been saved successfully. Stop & save can also save a take directly from the paused state.
- The pause location is saved. If the browser page is reloaded, the unsaved in-memory take cannot resume; the saved session returns to that section and asks you to re-record it. Completed audio remains saved.

Apple Voice Memos companion:
- Pause timing stops the timing run and discards the current incomplete section interval, without changing completed source ranges.
- The website cannot pause Apple's Voice Memos audio. Pause it in Voice Memos if needed.
- Resume & restart section or Restart current section requests a fresh sync marker, then Begin section. Read the current section again from the beginning. The interrupted source range is excluded from the exported segment timing.
- Stop & save while timing is paused keeps the session ready for a later restart. Paused sessions can be reopened at the interrupted section.

## Viewer timing

One viewer repetition per phrase. Default duration is `max(average recorded single-phrase repetition duration + buffer, minimum)`. The phrase duration is never combined with meaning, example, cue, intro, or outro. Browser audio uses decoded media duration when available, elapsed capture time otherwise. Voice Memos uses the marked phrase interval, which includes tap latency. Use the per-phrase exact duration to correct excess silence or tap delay. Before a phrase is recorded, the UI labels the fallback word-count estimate explicitly.

Timer previews show one smoothly shrinking horizontal line, no grey track, no numbers and no ticking. Each phrase's exact time can be adjusted after recording. Intro/outro have no viewer turns.

## Export contract

Schema v3, `mode: learn-and-practise`, `narratorRepetitions` holds the lesson phrase default (1 or 2), and `viewerRepetitions: 1`. The `phraseRepetitions` and `exampleRepetitions` maps give the actual count for each phrase ID. Each spoken entry includes `repetitionIndex` and `repetitionCount`. The first take keeps its original segment ID; a second take uses a unique `-repeat-2` suffix. Legacy Phase 1 importers must explicitly add v3 support; treating these teaching clips as twice-spoken phrases is incorrect.

- `lesson`: editable script and timing settings.
- `segments`: typed spoken sections and recording metadata, no binary blobs.
- `timeline`: ordered spoken sections and silent viewer turns with explicit start, end and duration in seconds. For browser audio each spoken entry references `clips/<segment-id>.<extension>`. Source clips have no automatic lead/tail trim. Normalize/center narration in the renderer.
- Each viewer turn references its phrase and carries its duration basis, silence instruction, and visual rules.
- Browser ZIP includes session.json, README.txt, and individual audio clips.
- Timing JSON can be downloaded incomplete, with `renderReady: false` and explicit missing IDs. Audio ZIP and full lesson preview require every spoken section.
- Voice Memos JSON uses ranges relative to the timing clock and an alignment warning; the external source recording is not included.

## Verification and limits

Run `node --test tests/*.test.cjs`. Core tests cover typed ordering, timer independence, overrides, exact one-turn policy, contiguous export timeline, incomplete recordings, Voice Memos ranges, and ZIP format.

This repository is the recording and timing web app. It does not contain the Windows/FFmpeg video generator; integration with that application's v3 importer must be validated in its repository. GitHub Pages hosts code, not user audio. The Phase 2 sessions are local to the current browser. This change does not implement authenticated cloud synchronization. Real iPhone microphone quality and Voice Memos background capture need a device test; desktop/test audio cannot establish those properties.
