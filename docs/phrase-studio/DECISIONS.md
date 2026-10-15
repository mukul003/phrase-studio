# Decisions

- Add Phase 2 to the existing static app at phase2.html, link both existing pages, preserve Phase 1 source and local session stores.
- Store Phase 2 recordings in a separate IndexedDB database to avoid destructive migrations.
- Typed spoken sections are intro, phrase, meaning, example, cue, outro. Viewer turns are generated silent timeline entries, never microphone recordings.
- Base viewer time only on the single phrase segment, plus configurable buffer/minimum or exact per-phrase override. Never use the explanation's duration.
- Export schema v3 with repetitions=1; never silently feed this to the Phase 1 repetitions=2 renderer.
- Provide Work Life content directly in the editor and support lesson JSON import/export for future topics.
- Voice Memos exports timing only and flags external alignment as required. Keep original audio separately. Browser mode exports actual clips in ZIP.
