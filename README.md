# Phrase Studio

- [Phase 1 — Listen & Repeat](https://mukul003.github.io/phrase-studio/)
- [Phase 1 — Voice Memos companion](https://mukul003.github.io/phrase-studio/voice-memos.html)
- [Phase 2 — Learn & Practise](https://mukul003.github.io/phrase-studio/phase2.html)

Paste a complete generated response into Phase 2 to fill the lesson automatically, or use the built-in generation prompt for future topics. Set phrases and examples to once or twice globally or per item. Phase 2 records the phrase, meaning, example and cue separately. The viewer timer uses only a single phrase repetition (averaging separately recorded takes), with configurable buffer/minimum and per-phrase overrides. A Work Life lesson is preloaded. Sessions remain on the current device until exported.

See [Phase 2 recording and export guide](docs/phrase-studio/PHASE2.md). The Windows video renderer is a separate application; it must support the schema-v3 timeline before using Phase 2 exports.

Tests: `node --test tests/*.test.cjs`.

The [ease-of-use workflow](docs/phrase-studio/USER_FLOW.md) defines the full script-to-video target and separates deployed features from Windows integration work. Use the [topic-only generation prompt](docs/phrase-studio/GENERATION_PROMPT.md), or enter a topic in the app and copy its prepared prompt.
