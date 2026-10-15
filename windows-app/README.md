# Phrase Studio — Windows video desk

A local ASP.NET Core application with a Python/FFmpeg media engine. Import a completed Phase 2 browser recording ZIP, review the lesson and choose **Generate video**. No cloud upload or paid service is involved.

## Run the Windows package

1. Open the repository's **Actions → Windows video app** and choose a successful run. Download **PhraseStudio-Windows-x64** from its Artifacts section (GitHub sign-in required).
2. Extract the entire ZIP to a writable folder. Run **Start-Phrase-Studio.cmd**. Keep its console open while using the app. The interface opens at `http://127.0.0.1:5278`.
3. In the online Phase 2 recorder, finish your browser recordings and export the recording ZIP. Import it into Video desk, then select **Generate video**. Play the result and choose **Save video**.

The portable build bundles the .NET runtime, Python engine, Pillow, FFmpeg and FFprobe. No separate runtime installation is needed. This first version is unsigned; physical Windows launch and microphone recordings remain acceptance checks until tested on the user's computer. Build artifacts expire after 30 days; rerun the workflow to recreate them. GitHub Pages hosts the recorder, not the local rendering service.

## Run from source on Windows

Install the .NET 8 SDK, Python 3.11+ with its `py` launcher, and FFmpeg/FFprobe on PATH. Double-click `Start-Windows.cmd`. It creates an isolated Python environment, installs the pinned Pillow dependency, builds the app and opens the browser. Internet is needed for initial setup. Subsequent imports/renders are local.

Develop on Linux/macOS: install .NET 8, Python, FFmpeg and the requirements; run `dotnet run --project windows-app/PhraseStudio.csproj`. Set `PHRASE_PYTHON` to the Python executable with Pillow installed. The development server binds only to IPv4 loopback on port 5278.

## What works

- Schema-v3 browser ZIP import, audio probing, complete lesson/order/repetition validation, readable section review and saved projects.
- Phrase/example repetition settings from the recorder; exactly one silent viewer turn after each cue. Measured individual phrase durations are averaged, then buffer/minimum applied; a manual practice override wins.
- Intro/outro preserved. Original ZIP and clips kept. Untrusted ZIP paths, duplicate names, excessive sizes, missing recordings, invalid durations and incomplete exports are rejected.
- Static branded slides, adaptive text wrapping and a shrinking colored practice line without a track, numbers or ticking. No footage or word highlighting.
- Full HD 1920×1080 or quick 1280×720 preview, both 30 fps H.264/yuv420p, AAC stereo 48 kHz and faststart. Narration is centered in both channels and normalized to -16 LUFS target. Viewer turns are silent.
- Progress, cancellation, playback, download and remembered quality preference. Output is checked with FFprobe before becoming available. Each render has a unique filename and report; previous renders are kept.
- Projects stored under `%LOCALAPPDATA%\PhraseStudio` (`PHRASE_DATA` can override). Closing/reopening the app retains imports, settings and completed exports. An interrupted render can be generated again.

## Current limits

Continuous Voice Memos audio and Adobe-enhanced audio need source matching/alignment; they are deliberately rejected rather than rendered with unreliable timing. Use the guided browser ZIP path for this version. Pause/resume and retake-current-section are in the Phase 2 recorder, before export. This video desk does not record a microphone or edit clips.

Background music, automated speech alignment/uncertainty review, one-take capture, cloud sync, installer/signing, GPU encoding, project deletion and persistent render-queue recovery are follow-up work. Rendering currently uses CPU H.264 for portability. Cancellation stops the render; temporary working files left by forced termination may be removed after the app closes. No changes are made to your original import.

A section whose text cannot fit on a readable slide fails with an actionable error instead of overflowing. Short conversational sections are the intended input. Imports are limited to 1 GB compressed / 2 GB extracted / 1,200 entries.

## Verify

From the repository root:

```
node --test tests/*.test.cjs
python -m pip install -r windows-app/engine/requirements.txt
python -m unittest discover -s windows-app/tests -v
dotnet build windows-app/PhraseStudio.csproj
```

The Windows workflow also publishes a self-contained host, exercises real HTTP import/settings/render/download/cancel, bundles the engine, then repeats HTTP checks with the packaged engine. A Microsoft Edge smoke test imports a ZIP, generates and loads a playable video, downloads it and restores the saved project after reload. The media tests generate a fixture through the real recorder export code, render an actual MP4, probe codecs/duration, inspect the shrinking line and check viewer silence. These synthetic checks do not replace listening to a real recorded lesson or testing your Windows desktop/browser.
