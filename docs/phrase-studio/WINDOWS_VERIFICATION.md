# Verified build — 15 October 2026

Application source commit: `e6bebd265f9828db0f2a1d176acf11a9c2f3d362`.

[Successful Windows build and checks](https://github.com/mukul003/phrase-studio/actions/runs/38739657819).
[Download Windows x64 package](https://github.com/mukul003/phrase-studio/actions/runs/38739657819/artifacts/11976111374) (GitHub sign-in required).

Package: PhraseStudio-Windows-x64, approximately 142 MB. Extract the entire archive and run **Start-Phrase-Studio.cmd**. Runtime/media dependencies are bundled. The artifact expires on 14 November 2026; use Actions → Windows video app → Run workflow to recreate it later.

Passed on the Windows GitHub runner:

- Self-contained .NET Windows x64 publish.
- 41 Node tests covering existing recorder/parser/timing behavior and video desk import/render/cancel controls.
- Six Python media tests: a real recorder-generated export contract; actual 1080p30 H.264/AAC export; metadata/duration checks; shrinking-line pixel checks; silent viewer interval; repeated phrases/examples and intro/outro; safe imports; measured phrase average/manual override; conservative quiet-edge trimming, retained internal pauses and rejection of a silent take.
- Real HTTP health/import/list/review/settings/render/download/cancel and cross-origin mutation rejection, first with the source engine and then with the bundled executable.
- Microsoft Edge: one ZIP import → Generate → video metadata loaded in preview → MP4 download → project/output restored after page reload. No page JavaScript errors. This is an automated interface check, not a listening assessment.

The media tests also passed in the Linux development workspace.

Still requiring acceptance on the user's computer: launch from the downloaded folder, a real microphone-recorded lesson and listening/visual review of the full exported video. No software has been installed on the user's physical computer from this cloud session.

Continuous Voice Memos/enhanced-audio alignment, optional music, one-take recording, signing/installer and GPU encoding remain follow-up features. The supported path for this build is a completed guided browser recording ZIP from Phase 2.
