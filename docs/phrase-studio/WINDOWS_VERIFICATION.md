# Verified build — 16 October 2026

Application source commit: `93940143a623be17635f6ce14889b14dfcc832c8`.

[Successful Windows build and checks](https://github.com/mukul003/phrase-studio/actions/runs/38853247101).
[Download Windows x64 package](https://github.com/mukul003/phrase-studio/actions/runs/38853247101/artifacts/12026400281) (GitHub sign-in required).

Package: PhraseStudio-Windows-x64, approximately 142 MB. Extract the entire archive and run **Start-Phrase-Studio.cmd**. Runtime/media dependencies are bundled. The artifact expires on 15 November 2026; use Actions → Windows video app → Run workflow to recreate it later.

Passed on the Windows GitHub runner:

- Self-contained .NET Windows x64 publish.
- 42 Node tests covering existing recorder/parser/timing behavior and video desk import/render/cancel controls.
- Eight Python media tests: a real recorder-generated export contract; actual 1080p30 H.264/AAC export; metadata/duration checks; shrinking-line pixel checks; silent viewer interval; repeated phrases/examples and intro/outro; safe imports; measured phrase average/manual override; conservative quiet-edge trimming, retained internal pauses and rejection of a silent take.
- Real HTTP health/import/list/review/settings/render/download/cancel and cross-origin mutation rejection, first with the source engine and then with the bundled executable.
- Microsoft Edge: one ZIP import → Generate → video metadata loaded in preview → MP4 download → project/output restored after page reload. No page JavaScript errors. This is an automated interface check, not a listening assessment.

The media tests also passed in the Linux development workspace.

Still requiring acceptance on the user's computer: launch from the downloaded folder, a real microphone-recorded lesson and listening/visual review of the full exported video. No software has been installed on the user's physical computer from this cloud session.

Continuous Voice Memos/enhanced-audio alignment, optional music, one-take recording, signing/installer and GPU encoding remain follow-up features. The supported path for this build is a completed guided browser recording ZIP from Phase 2.

Flow revision verified in this build: topic-only opening; target-phrase-only bodies with section headings; 1-second holds after phrase takes, 0.5-second holds after other spoken sections, and 1-second transitions between phrase groups. The remembered whoosh checkbox defaults off. Actual exported effects were checked in transition gaps, with silent viewer intervals preserved. API tests exercised the enabled sound option; Edge checked that its preference survived reload.
