# Decisions

- Add Phase 2 to the existing static app at phase2.html, link both existing pages, preserve Phase 1 source and local session stores.
- Store Phase 2 recordings in a separate IndexedDB database to avoid destructive migrations.
- Typed spoken sections are intro, phrase, meaning, example, cue, outro. Viewer turns are generated silent timeline entries, never microphone recordings.
- Base viewer time only on the single phrase segment, plus configurable buffer/minimum or exact per-phrase override. Never use the explanation's duration.
- Export schema v3 with explicit repetition defaults, per-phrase maps and per-take indices; viewer repetitions stay at one; never silently feed this to the Phase 1 repetitions=2 renderer.
- Provide Work Life content directly in the editor and support lesson JSON import/export for future topics.
- Voice Memos exports timing only and flags external alignment as required. Keep original audio separately. Browser mode exports actual clips in ZIP.

- Add a deterministic bulk-paste parser for labeled text/Markdown/tables/JSON. Validate the whole parsed lesson before replacing editor fields. Generate missing speaking cues automatically, but never guess required summary/example boundaries.
- Allow once/twice narrator phrases and examples globally or per item, using separately timed takes. Viewer duration averages individual phrase takes only.
- Keep the existing Phase 2 storage database and first-take IDs stable so saved sessions continue to open. New repetition settings apply to newly created sessions.

- Ease of use is a product acceptance requirement: topic → generate → one paste → natural recording → one package → Generate. See USER_FLOW.md for implemented/pending boundaries.
- Retain guided capture until actual Windows automatic alignment is integrated; do not make an unsupported one-take workflow the default.
- Store non-secret recording preferences locally; respect explicit script settings and preserve preferences otherwise. Keep the microphone stream across Next transitions and release it on Stop, final save or error.

- User correction, 15 October 2026: the Windows app is not implemented. Plan it as a new build consuming the live recorder's exports. No existing Windows project source is a prerequisite; this supersedes earlier statements asking the user to supply a current Windows repository/ZIP.

- Pause/resume applies to native browser MediaRecorder; elapsed fallback excludes pause gaps. Restart discards only the unfinished take and retains completed sections/any previous successful take until its replacement saves.
- The Voice Memos companion cannot control Apple's recording. Pause discards only the unfinished timing interval, and resume/restart uses a new sync anchor for the same section.
- Save the interrupted section checkpoint; after a reload require a clean re-record of an unsaved take rather than claiming in-memory audio can be restored.

- Script voice revision: keep the parser labels as metadata while writing the spoken fields around connected everyday moments. Replace repetitive textbook definitions and repeated example/cue openers with varied, clear narration. Include a concrete style reference and a silent read-aloud editing pass in the generation prompt. Script quality is editorial; parser tests establish compatibility, not that a model's future audio will sound natural.
