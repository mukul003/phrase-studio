# Continuation

Use USER_FLOW.md as the ease-of-use acceptance contract for all further work.

Implemented: topic prompt builder, one-paste parser, remembered settings, phrase/example repetitions, next-section preview, fixed recording controls, local persistence and typed audio/timing exports. Guided browser recording reuses its microphone stream between adjacent sections. Existing sessions remain intact.

Pending: build the Windows video generator from scratch. The user confirmed that it has not been implemented; there is no existing project ZIP/repository to request.
1. Create the Windows app from USER_FLOW.md and the saved media/export requirements, with a simple local UI and clear installation/start instructions.
2. Implement schema-v3 import, including repetition maps and explicit viewer-turn durations.
3. Add single-package import and automatic alignment for continuous recordings, originals and enhanced audio. Review uncertain boundaries only.
4. Connect saved presets and one Generate action to 1080p30 output with QA. Preserve intro/outro and a single viewer turn per phrase.
5. Enable one-take capture as the normal path only after alignment/rendering is verified.

Physical iPhone microphone/Voice Memos testing and authenticated Worker sync remain separate integration checks. Cloud sync is not implemented by this change.
