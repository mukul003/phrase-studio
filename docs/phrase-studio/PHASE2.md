# Phase 2 — Learn & Practise

Open `phase2.html` from either Phase 1 page. The Work Life lesson is preloaded, including the conversational introduction and outro. All words are editable. Saved Phase 1 sessions remain in their existing storage and formats.

## Recording

Choose browser microphone or Apple Voice Memos timing companion before creating a session. Read every section **once**. The sequence is intro, then phrase / meaning / example / cue for each phrase, then outro. The silent viewer turns are generated from metadata; do not record them.

Browser: Record section, then Save & next. Next immediately starts recording the next section. Stop & save ends recording without advancing; use Next section to navigate afterward. Any section can be revisited and retaken. Complete all sections to enable the audio ZIP and full audio/timer preview. The microphone input meter flags clipping.

Voice Memos: Start Apple's recording, return to the page, Start timing, speak the shown session marker, then Begin section. Tap Save & next at each boundary. After the final section, stop Voice Memos separately. Download the JSON and retain the matching M4A. After a stopped/reloaded timing session, speak a fresh marker to anchor the new timing run. Each run is recorded in events. The source audio needs manual marker alignment in the video generator, especially after audio enhancement.

## Viewer timing

One viewer repetition per phrase. Default duration is `max(recorded phrase duration + buffer, minimum)`. The phrase duration is never combined with meaning, example, cue, intro, or outro. Browser audio uses decoded media duration when available, elapsed capture time otherwise. Voice Memos uses the marked phrase interval, which includes tap latency. Use the per-phrase exact duration to correct excess silence or tap delay. Before a phrase is recorded, the UI labels the fallback word-count estimate explicitly.

Timer previews show one smoothly shrinking horizontal line, no grey track, no numbers and no ticking. Each phrase's exact time can be adjusted after recording. Intro/outro have no viewer turns.

## Export contract

Schema v3, `mode: learn-and-practise`, `narratorRepetitions: 1`, `viewerRepetitions: 1`. Legacy Phase 1 importers must explicitly add v3 support; treating these teaching clips as twice-spoken phrases is incorrect.

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
