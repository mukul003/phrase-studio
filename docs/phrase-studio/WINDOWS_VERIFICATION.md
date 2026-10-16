# Verified build — 16 October 2026

Application source commit: `4e7d00672e017206d06e0e434f70be7c5ab8fa1e`.

[Successful Windows build and checks](https://github.com/mukul003/phrase-studio/actions/runs/38860191742).
[Download Windows x64 package](https://github.com/mukul003/phrase-studio/actions/runs/38860191742/artifacts/12028579347) (GitHub sign-in required).

Package: PhraseStudio-Windows-x64, approximately 142 MB. Extract the entire archive and run **Start-Phrase-Studio.cmd**. Runtime/media dependencies are bundled. The artifact expires on 15 November 2026; use Actions → Windows video app → Run workflow to recreate it later.

Passed on the Windows GitHub runner:

- Self-contained .NET Windows x64 publish.
- 43 Node tests covering existing recorder/parser/timing behavior and video desk import/render/cancel controls.
- Nine Python media/PDF tests: a real recorder-generated export contract; actual 1080p30 H.264/AAC export; metadata/duration checks; shrinking-line pixel checks; silent viewer interval; repeated phrases/examples and intro/outro; safe imports; measured phrase average/manual override; conservative quiet-edge trimming, retained internal pauses and rejection of a silent take.
- Real HTTP health/import/list/review/settings/render/download/cancel and cross-origin mutation rejection, first with the source engine and then with the bundled executable.
- Microsoft Edge: one ZIP import → Generate → video metadata loaded in preview → MP4 download → project/output restored after page reload. No page JavaScript errors. This is an automated interface check, not a listening assessment.

The media tests also passed in the Linux development workspace.

Still requiring acceptance on the user's computer: launch from the downloaded folder, a real microphone-recorded lesson and listening/visual review of the full exported video. No software has been installed on the user's physical computer from this cloud session.

Continuous Voice Memos/enhanced-audio alignment, optional music, one-take recording, signing/installer and GPU encoding remain follow-up features. The supported path for this build is a completed guided browser recording ZIP from Phase 2.

Flow revision verified in this build: topic-only opening; target-phrase-only bodies with section headings; 1-second holds after phrase takes, 0.5-second holds after other spoken sections, and 1-second transitions between phrase groups. The remembered whoosh checkbox defaults off. Actual exported effects were checked in transition gaps, with silent viewer intervals preserved. API tests exercised the enabled sound option; Edge checked that its preference survived reload.

Visual revision verified: `studio-cards-v1` uses layered cream/navy cards, bold text, section colour accents and locally drawn conversation artwork. Topic titles with an em dash use a separate headline and subtitle. Linux layout checks cover contrast and the unpainted practice-timer lane at full resolution. The real cleaned ten-phrase lesson was rendered at 1080p30: 9,702 frames / 323.4 seconds, with matching audio/video durations, 10 silent practice turns and nine transition effects. AAC audio bytes match the previous cleaned export exactly.

PDF/theme revision verified: the remembered **Create slide PDF** option defaults on for new and older settings. Real API checks generated and downloaded a PDF, verified page count and order, rerendered with PDF disabled, checked the missing PDF route returns 404, and retained cancellation behaviour. The same checks passed with the bundled engine. Edge downloaded both outputs and restored the PDF link after reload. Nine local/Windows media tests cover landscape pages, source ordering, opt-out and custom-theme validation. A short two-phrase export without transition sound now normalizes audio to frame-exact PCM before AAC muxing, preventing a resampler tail from creating A/V duration drift.

`theme.json` is shipped beside the app and read at each render. `LAYOUT_GUIDE.md` documents manual style changes and the rebuild/install workflow for a completely different composition. A real custom-theme preview and its PDF were checked locally, including stored theme metadata and matching A/V duration. The current cleaned lesson's 61 slide images were also converted to a PDF and visually reviewed; no new video was needed for that PDF.
