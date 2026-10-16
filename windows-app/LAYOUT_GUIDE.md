# Changing the video and PDF design

## Change colours, type size and branding without rebuilding

1. Open the extracted Phrase Studio application folder (the folder containing `Start-Phrase-Studio.cmd`).
2. Make a backup of `theme.json`, then open it in Notepad or VS Code.
3. Edit the values, save the file, and generate a **Quick preview** in the app. The engine reads the file at the start of each render; no restart is required.
4. When satisfied, generate the Full HD version. Both the video and its PDF use the same theme snapshot.

Useful fields:

| Field | Controls |
| --- | --- |
| `background` | Main slide background, including the timer lane |
| `card` / `ink` | Card colour / text colour |
| `foreground` | Channel heading text colour |
| `accent` | Practice timer line and opening accent |
| `muted` | Footer topic text |
| `brand` | Channel heading (maximum 45 characters) |
| `sectionColors` | Separate accent colour for each section |
| `phraseMaxSize` | Maximum phrase text size, from 26 to 110 |
| `titleMaxSize` | Maximum opening headline size, from 40 to 140 |
| `cornerRadius` | Phrase card corner rounding, from 0 to 80 |
| `artwork` | `true` shows conversation artwork; `false` hides it |

Colours must be written as `#RRGGBB`, such as `#ffffff`. Keep JSON quotes and commas intact. Text automatically shrinks/wraps to fit. Keep text and card colours sufficiently different for reading on phones. The theme may contain only the fields you want to override; missing values use the built-in design. A missing file uses the complete built-in theme. Invalid values produce an actionable error before rendering begins.

An example minimal replacement for `theme.json`:

```json
{
  "background": "#15252e",
  "card": "#ffffff",
  "ink": "#15252e",
  "accent": "#eeae57",
  "brand": "FLUENT ENGLISH FOR YOU",
  "phraseMaxSize": 82,
  "cornerRadius": 20,
  "artwork": false
}
```

Changing this file affects future exports, not existing MP4/PDF files. Export reports store the resolved theme so the design can be reproduced. Keep a backup of your custom theme when installing a newer app package; copy it into the new folder after extracting.

## Replace the layout completely

The app draws slides programmatically; it does not import PowerPoint templates. A completely different composition (new element positions, split columns, illustrations or a different card system) requires editing `slide()` in `windows-app/engine/studio.py`. Preserve `display_text()` for phrase-only bodies, the heading for each section and the practice-line lane (currently y=910 at 1920x1080). If moving the timer, update the viewer overlay coordinates in `render()` and the timer tests too.

For the portable Windows app, editing `studio.py` beside the app is **not enough**: the packaged `phrase-engine.exe` takes precedence. Commit the renderer change to GitHub, let **Actions → Windows video app** finish, download the new **PhraseStudio-Windows-x64** artifact and extract it into a new folder. Copy over your custom `theme.json`, then run `Start-Phrase-Studio.cmd`. Existing projects remain in `%LOCALAPPDATA%\PhraseStudio`.

The source checkout launched through `Start-Windows.cmd` runs the Python renderer directly. In that development mode, editing `studio.py` takes effect on the next render without packaging. The documented tests and the Windows workflow should pass before distributing a redesigned engine.

## Automatic slide PDF

**Create slide PDF** is enabled by default, including when loading older saved settings. Turning it off is remembered. A successful video render generates a matching landscape PDF automatically, one page per rendered section in video order, including opening/outro, transitions, repeated takes and practice slides. It is a static copy of the slide images, without audio or an animated timer. It does not add the spoken explanations/examples to the page.

The video and PDF are stored together in the local project folder. **Save video** and **Save slide PDF** download them individually. The PDF button remains available when reopening a completed project. If PDF creation fails, the finished video remains available and the app explains the PDF error. Old videos need to be regenerated once to create their PDF.
