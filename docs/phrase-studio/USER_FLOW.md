# Phrase Studio — ease-of-use requirements

User feedback, 15 October 2026: generating a script, formatting it, entering fields, changing recording sections, moving audio/JSON and rendering must feel like one smooth process with minimal manual intervention. This is a product acceptance requirement for every future phase.

## Target happy path

1. Enter one topic. Copy the complete prompt, or use it in ChatGPT with only the topic replaced. Generate 10 short, useful sentences with conversational summaries/examples and friendly intro/outro. Keep the output natural to read. Format labels are app metadata, never spoken instructions.
2. Paste the entire response once. Detect the lesson, validate it and create a recording session. Make field editing optional. Remember chosen repetition counts, recording source, microphone mode and the user's template preferences. A rough script may be reformatted by ChatGPT, but an extra formatting conversation must not be mandatory for the standard prompt.
3. Record naturally. The preferred future workflow is one uninterrupted take with optional pause/resume and retake-last-block. Show a readable teleprompter and upcoming text. No typing timestamps, repeating text in the script to enable double takes, or visiting dozens of configuration fields. Continue to offer the guided per-section mode for precise capture and retakes.
4. Transfer one recording package. Browser recording packages audio, script, repetitions, settings and timing together. For Voice Memos, select its single recording and match it to the saved script/session automatically; do not ask the user to rebuild JSON. Original and enhanced audio remain identifiable and read-only.
5. Generate the video with one saved preset. Automatically align spoken text, detect phrase/explanation/example/cue boundaries, insert viewer silence, compose static branded slides, mix optional quiet music, validate and export 1080p30. Offer review at low-confidence locations rather than demanding adjustment of every boundary.

## What is implemented in this repository

- Topic field creates a ready-to-copy generation prompt. The full reusable prompt is in GENERATION_PROMPT.md.
- One paste parses labels/Markdown/tables/JSON; Start auto-parses new text. Detailed fields are optional.
- Once/twice settings for phrases/examples globally and individually. Repetition is configuration, not duplicated script text.
- Saved recording preferences survive new imports when the script does not explicitly override them.
- Guided recording provides next-section text, fixed controls, optional progress/details and microphone-stream reuse between adjacent clips. Browser capture supports Pause/Resume and Restart current section; Voice Memos timing supports pause and a fresh-marker restart. Completed sections remain saved.
- Browser audio ZIP / Voice Memos timing JSON and typed timeline are implemented. One viewer turn per phrase uses the duration of a single phrase repetition, never combined teaching audio.

## Pending: build the Windows video generator

User clarification, 15 October 2026: the Windows application has not been implemented. It is a new build; no current Windows repository or project ZIP is required from the user. This supersedes the earlier assumption that an existing Windows app needed integration.

Build the Windows application from the saved Phrase Studio requirements and the deployed recorder's schema-v3 contract. Include a simple local UI, single-package import, automatic source matching/alignment, saved render presets and one Generate action. Reuse proven utilities where appropriate, but do not assume older TTS repositories are the new application.

One-take recording should only become the default once automatic alignment and rendering have been verified with actual recordings. Until then, guided section recording supplies reliable timings. The current web app does not automatically generate the final MP4.

## Non-negotiable media rules

- Preserve the spoken intro and outro. Remove only the spoken sync marker and unwanted surrounding silence, not the introduction. Recover after pauses/restarts with explicit run anchors.
- Speak phrases/examples once or twice as configured; keep exactly one silent viewer repetition after each cue.
- Derive the viewer duration from an individually aligned phrase repetition (or average of individual takes), with saved buffer/minimum and optional override. Longer explanations/examples must not lengthen it.
- Never assume Adobe enhancement preserves silence or offsets. Re-align changed audio, flag uncertainty, and preserve originals.
- Current visual template: clean static slides; no footage backgrounds; no word-by-word highlighting; a single shrinking horizontal line without numbers, grey track or ticking.
- Background music optional, quiet enough for clear speech. Center narration in stereo.
- Master export: 1920×1080, 30fps, H.264/yuv420p, AAC stereo 48kHz, faststart. Validate ordering, duration, audio and video output.

## Acceptance checks for the complete flow

A new topic should require only the topic name, one paste, recording, one import/transfer and Generate. No field-by-field editing, repeated settings, manual clip stitching or required timestamp calculations on the normal path. A mistake should cost one block retake, not a whole new session. Incomplete recordings and uncertain alignment must be identified before publishing. Preserve existing local sessions and backward-compatible schema handling.
