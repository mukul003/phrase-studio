# Continuation

Use USER_FLOW.md as the ease-of-use acceptance contract for all further work.

Implemented: topic prompt builder, one-paste parser, remembered settings, phrase/example repetitions, next-section preview, fixed recording controls, local persistence and typed audio/timing exports. Guided browser recording reuses its microphone stream between adjacent sections. Existing sessions remain intact.

Pending in the actual Windows project:
1. Identify and inspect the current Windows app source; do not assume an older TTS repository is the running app.
2. Add schema-v3 import, including repetition maps and explicit viewer-turn durations.
3. Add single-package import and automatic alignment for continuous recordings, originals and enhanced audio. Review uncertain boundaries only.
4. Connect saved presets and one Generate action to 1080p30 output with QA. Preserve intro/outro and a single viewer turn per phrase.
5. Enable one-take capture as the normal path only after alignment/rendering is verified.

Physical iPhone microphone/Voice Memos testing and authenticated Worker sync remain separate integration checks. Cloud sync is not implemented by this change.
