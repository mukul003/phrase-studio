"""Local Phrase Studio media engine. No network calls; imported originals are immutable."""
import argparse
import array
import copy
from functools import lru_cache
import json
import math
import os
import re
import random
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import wave
import zipfile
from PIL import Image, ImageDraw, ImageFont

FPS = 30
BG = '#101e2b'
FG = '#f4f0e6'
ACCENT = '#e1b46a'


DEFAULT_THEME = {
    'background': BG, 'foreground': FG, 'card': '#f4f0e6', 'ink': BG,
    'accent': ACCENT, 'muted': '#93a9b9', 'brand': 'FLUENT ENGLISH FOR YOU',
    'phraseMaxSize': 88, 'titleMaxSize': 116, 'cornerRadius': 42,
    'artwork': True,
    'sectionColors': {'phrase': '#e1b46a', 'meaning': '#8ddacb', 'example': '#a9cafa',
                      'cue': '#f3afa1', 'viewer-turn': '#e1b46a', 'transition': '#8ddacb', 'outro': '#a9cafa'}
}


def load_theme(path=None):
    theme = copy.deepcopy(DEFAULT_THEME)
    if path is None or not path.exists():
        return theme
    try:
        custom = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(custom, dict) or set(custom) - set(theme):
            raise ValueError('unknown theme fields')
        for key, value in custom.items():
            if key == 'sectionColors':
                if not isinstance(value, dict) or set(value) - set(theme[key]):
                    raise ValueError('unknown section colours')
                theme[key].update(value)
            else:
                theme[key] = value
        for key in ('background', 'foreground', 'card', 'ink', 'accent', 'muted'):
            if not isinstance(theme[key], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', theme[key]):
                raise ValueError(key + ' must be a #RRGGBB colour')
        if any(not isinstance(v, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', v) for v in theme['sectionColors'].values()):
            raise ValueError('section colours must use #RRGGBB')
        for key, low, high in [('phraseMaxSize', 26, 110), ('titleMaxSize', 40, 140), ('cornerRadius', 0, 80)]:
            if type(theme[key]) is not int or not low <= theme[key] <= high:
                raise ValueError(f'{key} must be an integer from {low} to {high}')
        if type(theme['artwork']) is not bool or not isinstance(theme['brand'], str) or len(theme['brand']) > 45:
            raise ValueError('artwork must be true/false and brand at most 45 characters')
        return theme
    except (ValueError, TypeError) as error:
        raise ValueError(f'Check theme.json: {error}') from error


def slides_pdf(images, output):
    """Append one page at a time to keep large lessons within bounded memory."""
    if not images:
        raise ValueError('No slides available for PDF')
    temporary = output.with_suffix('.pdf.tmp')
    try:
        for index, path in enumerate(images):
            with Image.open(path) as source:
                with source.convert('RGB') as page:
                    page.save(temporary, format='PDF', resolution=144, append=index > 0,
                              title='Phrase Studio lesson slides')
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def emit(**value):
    print(json.dumps(value), flush=True)


def run(args):
    p = subprocess.run([str(x) for x in args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if p.returncode:
        raise ValueError(p.stderr[-3000:] or 'Media command failed')
    return p.stdout


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path]))


def duration(path):
    d = probe(path)
    streams = [s for s in d['streams'] if s['codec_type'] == 'audio']
    if not streams:
        raise ValueError(f'No audio in {Path(path).name}')
    return float(streams[0].get('duration') or d['format']['duration'])


def audio_window(path, length):
    """Trim only quiet edges; preserve every internal pause and the original file."""
    result = subprocess.run(['ffmpeg', '-v', 'info', '-nostdin', '-i', str(path), '-vn', '-af', 'silencedetect=noise=-45dB:d=0.25', '-f', 'null', '-'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise ValueError(result.stderr[-2000:])
    starts = [float(x) for x in re.findall(r'silence_start: ([0-9.e+-]+)', result.stderr)]
    ends = [float(x) for x in re.findall(r'silence_end: ([0-9.e+-]+)', result.stderr)]
    start, end = 0.0, length
    if starts and ends and starts[0] < .03:
        if ends[0] >= length - .1:
            raise ValueError(f'{Path(path).name}: recording is silent. Re-record this section.')
        start = max(0, ends[0] - .1)
    if starts and ends and ends[-1] >= length - .1:
        end = min(length, starts[-1] + .1)
    if end <= start:
        raise ValueError('Recording has no usable speech; re-record this section')
    return start, end


def safe_member(name):
    p = PurePosixPath(name)
    return bool(name) and '\\' not in name and ':' not in name and not p.is_absolute() and '..' not in p.parts


def expected_sections(lesson):
    expected = []
    if lesson.get('intro', '').strip():
        expected.append(('intro', None))
    for phrase in lesson['phrases']:
        pid = phrase['id']
        for kind in ('phrase', 'meaning', 'example', 'cue'):
            count = phrase.get(kind + 'Repetitions', lesson.get(kind + 'Repetitions', 1)) if kind in ('phrase', 'example') else 1
            if count not in (1, 2):
                raise ValueError('Repetitions must be one or two')
            expected.extend([(kind, pid)] * count)
        expected.append(('viewer-turn', pid))
    if lesson.get('outro', '').strip():
        expected.append(('outro', None))
    return expected


def display_text(doc, section):
    if section['type'] in ('intro', 'outro', 'title'):
        return doc['title']
    phrase = next((p for p in doc['lesson']['phrases'] if p['id'] == section.get('phraseId')), None)
    return phrase['phrase'] if phrase else section.get('text', '')


def build_render_plan(doc):
    """Pacing is separate from speech duration and never lengthens a viewer turn."""
    plan = []
    if not any(s['type'] == 'intro' for s in doc['timeline']):
        plan.append({'id': 'opening-title', 'type': 'title', 'text': doc['title'], 'frames': 2 * FPS, 'audio': 'silence'})
    previous_phrase = None
    for original in doc['timeline']:
        s = copy.deepcopy(original)
        pid = s.get('phraseId')
        if s['type'] == 'phrase' and previous_phrase is not None and pid != previous_phrase:
            plan.append({'id': pid + '-transition', 'type': 'transition', 'phraseId': pid, 'text': '', 'frames': FPS, 'audio': 'silence'})
        if s['type'] == 'phrase':
            previous_phrase = pid
        s['speechFrames'] = s.get('frames', math.ceil(s['durationSeconds'] * FPS))
        s['holdSeconds'] = 0 if s['type'] == 'viewer-turn' else 1 if s['type'] == 'phrase' else .5
        s['frames'] = s['speechFrames'] + round(s['holdSeconds'] * FPS)
        plan.append(s)
    at = 0
    for s in plan:
        s['displayText'] = display_text(doc, s)
        s['startSeconds'] = at / FPS
        at += s['frames']
        s['endSeconds'] = at / FPS
    return plan


def whoosh_pcm(frames, sample_rate=48000):
    """Original, quiet, shaped wind sound; no external media download."""
    count = round(frames / FPS * sample_rate)
    active = min(count, round(.55 * sample_rate))
    rng = random.Random(9563)
    samples = array.array('h')
    slow = fast = 0.0
    shaped = []
    for i in range(active):
        t = i / max(1, active - 1)
        noise = rng.uniform(-1, 1)
        cutoff = 500 + 4000 * math.sin(math.pi * t) ** 2
        alpha = 1 - math.exp(-2 * math.pi * cutoff / sample_rate)
        fast += alpha * (noise - fast)
        slow += .025 * (noise - slow)
        shaped.append((fast - slow) * math.sin(math.pi * t) ** 2)
    peak = max(map(abs, shaped), default=1) or 1
    for value in shaped:
        sample = round(value / peak * .08 * 32767)
        samples.extend((sample, sample))
    samples.extend([0] * ((count - active) * 2))
    if sys.byteorder != 'little':
        samples.byteswap()
    return samples.tobytes()


def write_effects(timeline, path):
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2)
        out.setsampwidth(2)
        out.setframerate(48000)
        for s in timeline:
            if s['type'] == 'transition':
                out.writeframesraw(whoosh_pcm(s['frames']))
            else:
                remaining = round(s['frames'] / FPS * 48000)
                while remaining:
                    count = min(remaining, 65536)
                    out.writeframesraw(bytes(count * 4))
                    remaining -= count


def validate(root):
    manifest = root / 'session.json'
    if manifest.stat().st_size > 5_000_000:
        raise ValueError('Session metadata is too large')
    doc = json.loads(manifest.read_text(encoding='utf-8-sig'))
    if doc.get('schemaVersion') != 3 or not doc.get('renderReady') or doc.get('incompleteSegmentIds'):
        raise ValueError('Export a completed schema-v3 recording ZIP from Phase 2')
    if doc.get('source') != 'browser' or doc.get('requiresSourceAudio'):
        raise ValueError('Voice Memos needs source alignment. Import a completed browser recording ZIP for this version.')
    lesson = doc['lesson']
    phrases = lesson['phrases']
    if not 1 <= len(phrases) <= 100 or len({p['id'] for p in phrases}) != len(phrases):
        raise ValueError('Invalid phrase list')
    timeline = doc['timeline']
    if [(s['type'], s.get('phraseId')) for s in timeline] != expected_sections(lesson):
        raise ValueError('Timeline does not match lesson order or repetition settings')
    if len({s['id'] for s in timeline}) != len(timeline):
        raise ValueError('Duplicate timeline sections')
    warnings = []
    measured = {}
    trimmed_count = 0
    for s in timeline:
        d = float(s['durationSeconds'])
        if not math.isfinite(d) or not 0 < d <= 1800:
            raise ValueError('Invalid section duration')
        if len(s.get('text', '')) > 6000:
            raise ValueError('Section text is too long')
        if s['type'] == 'viewer-turn':
            if s.get('repetitions') != 1:
                raise ValueError('Each phrase needs exactly one viewer turn')
            continue
        name = s['source']['file']
        if not safe_member(name) or not name.startswith('clips/'):
            raise ValueError('Unsafe audio file path')
        path = root / name
        if not path.is_file():
            raise ValueError(f'Missing recording: {name}')
        actual = duration(path)
        if not math.isfinite(actual) or actual <= 0 or actual > 1800:
            raise ValueError('Invalid recorded audio duration')
        if abs(actual - d) > .25:
            warnings.append(f"{s['id']}: using measured audio duration ({actual:.2f}s instead of {d:.2f}s).")
        trim_start, trim_end = audio_window(path, actual)
        if trim_start > .05 or actual - trim_end > .05:
            trimmed_count += 1
        s['source']['trimStartSeconds'] = trim_start
        s['source']['trimEndSeconds'] = trim_end
        s['durationSeconds'] = trim_end - trim_start
        if s['type'] == 'phrase':
            measured.setdefault(s['phraseId'], []).append(s['durationSeconds'])
    for s in timeline:
        if s['type'] != 'viewer-turn':
            continue
        p = next(p for p in phrases if p['id'] == s['phraseId'])
        if p.get('practiceSeconds') is not None:
            d = float(p['practiceSeconds'])
            if not math.isfinite(d) or not 1 <= d <= 120:
                raise ValueError('Practice override must be 1–120 seconds')
        else:
            buffer = float(lesson.get('bufferSeconds', 1))
            minimum = float(lesson.get('minimumPracticeSeconds', 3))
            if not (math.isfinite(buffer) and 0 <= buffer <= 30 and math.isfinite(minimum) and 1 <= minimum <= 120):
                raise ValueError('Invalid viewer timing settings')
            values = measured[s['phraseId']]
            d = max(minimum, sum(values) / len(values) + buffer)
        s['durationSeconds'] = d
    at = 0
    for s in timeline:
        # Round up each audio section to a whole frame: no cumulative A/V drift.
        s['frames'] = math.ceil(s['durationSeconds'] * FPS)
        s['startSeconds'] = at / FPS
        at += s['frames']
        s['endSeconds'] = at / FPS
    doc['sourceTimeline'] = copy.deepcopy(timeline)
    doc['timeline'] = build_render_plan(doc)
    doc['totalDurationSeconds'] = doc['timeline'][-1]['endSeconds']
    doc['renderFlowVersion'] = 2
    doc['pacing'] = {'afterPhraseSeconds': 1, 'afterOtherSpokenSectionsSeconds': .5, 'betweenPhrasesSeconds': 1}
    if trimmed_count:
        warnings.append(f'Quiet recording edges removed from {trimmed_count} sections. Original audio is kept.')
    doc['warnings'] = warnings
    return doc


def import_package(package, root):
    root.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(package) as archive:
            entries = archive.infolist()
            names = [i.filename for i in entries]
            if len(entries) > 1200 or len({n.casefold() for n in names}) != len(names) or sum(i.file_size for i in entries) > 2_000_000_000:
                raise ValueError('Package exceeds limits or contains duplicate files')
            if 'session.json' not in names:
                raise ValueError('This ZIP has no session.json; use Phase 2 Export recording ZIP')
            for info in entries:
                if not safe_member(info.filename) or ((info.external_attr >> 16) & 0o170000) == 0o120000:
                    raise ValueError('Unsafe ZIP entry')
                if info.is_dir():
                    continue
                target = root / info.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open('wb') as out:
                    shutil.copyfileobj(source, out)
        doc = validate(root)
        (root / 'project.json').write_text(json.dumps(doc, indent=2), encoding='utf-8')
        shutil.copyfile(package, root / 'original-package.zip')
        return doc
    except BaseException:
        shutil.rmtree(root, ignore_errors=True)
        raise


@lru_cache(maxsize=128)
def font(size, bold=False):
    filename = 'segoeuib.ttf' if bold else 'segoeui.ttf'
    linux_name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    for candidate in [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / filename, Path('/usr/share/fonts/truetype/dejavu') / linux_name]:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


def wrapped(draw, text, f, width):
    lines = []
    for paragraph in text.splitlines() or ['']:
        current = ''
        for word in paragraph.split():
            if draw.textlength(word, font=f) > width:
                raise ValueError('Text contains an unusually long word; shorten it before rendering')
            new = (current + ' ' + word).strip()
            if current and draw.textlength(new, font=f) > width:
                lines.append(current)
                current = word
            else:
                current = new
        lines.append(current)
    return lines


def slide(doc, section, path, width, height, theme=None):
    """Native studio cards: readable type, section colours and conversation artwork."""
    theme = theme or DEFAULT_THEME
    background, foreground, ink = theme['background'], theme['foreground'], theme['ink']
    text = display_text(doc, section)
    if len(text) > 6000:
        raise ValueError(f"Section {section['id']} has too much text for one slide")
    image = Image.new('RGB', (width, height), background)
    draw = ImageDraw.Draw(image)
    scale = width / 1920
    def pos(n): return round(n * scale)
    def box(bounds, fill, radius=0, outline=None, stroke=2):
        draw.rounded_rectangle(tuple(pos(v) for v in bounds), radius=pos(radius), fill=fill, outline=outline, width=max(1, pos(stroke)))
    def line(points, fill, stroke=3):
        draw.line([(pos(x), pos(y)) for x, y in points], fill=fill, width=max(1, pos(stroke)), joint='curve')
    def label(x, y, value, size, colour, bold=False):
        draw.text((pos(x), pos(y)), value, font=font(pos(size), bold), fill=colour)
    def fitted(value, bounds, largest, smallest, colour, centered=False):
        x, y, w, h = bounds
        for size in range(largest, smallest - 1, -2):
            f = font(pos(size), True)
            lines = wrapped(draw, value, f, pos(w))
            spacing = pos(size * 1.32)
            if len(lines) * spacing <= pos(h):
                break
        else:
            raise ValueError(f"Section {section['id']} has too much text for one slide")
        top = pos(y) + (pos(h) - len(lines) * spacing) // 2
        for item in lines:
            left = pos(x) + ((pos(w) - draw.textlength(item, font=f)) / 2 if centered else 0)
            draw.text((left, top), item, font=f, fill=colour)
            top += spacing
    kind = section['type']
    palette = theme['sectionColors']
    accent = palette.get(kind, theme['accent'])
    # Decorative shapes live above the practice lane; its background stays solid navy.
    if theme['artwork']:
        box((1460, 110, 1870, 815), '#162b3a', 110)
        box((1530, 160, 1800, 760), '#1c3643', 100)
    if kind in ('intro', 'title'):
        # Opening contains topic text only, surrounded by abstract conversation shapes.
        box((140, 180, 1760, 850), '#223f49', 58)
        box((116, 156, 1736, 826), theme['card'], 58)
        box((176, 220, 188, 752), '#62b8a6', 6)
        title_parts = text.split(' — ', 1)
        if len(title_parts) == 2 and all(title_parts):
            fitted(title_parts[0], (246, 285, 1350, 260), theme['titleMaxSize'], 40, ink, True)
            box((846, 572, 1006, 580), '#62b8a6', 4)
            fitted(title_parts[1], (286, 620, 1270, 115), 52, 32, '#375e67', True)
        else:
            fitted(text, (246, 270, 1350, 470), theme['titleMaxSize'], 40, ink, True)
        box((1570, 110, 1680, 128), theme['accent'], 9)
        box((1710, 110, 1740, 128), '#8ddacb', 9)
        image.save(path)
        return
    label(130, 64, theme['brand'], 26, foreground, True)
    # A bounded window of lesson dots remains legible for lessons of any length.
    phrases = doc['lesson']['phrases']
    index = next((i for i, p in enumerate(phrases) if p['id'] == section.get('phraseId')), None)
    if index is not None:
        start = max(0, min(index - 5, len(phrases) - 12))
        shown = phrases[start:start + 12]
        for i, _ in enumerate(shown):
            x = 1790 - (len(shown) - 1 - i) * 27
            box((x - 5, 80, x + 5, 90), accent if start + i <= index else '#3a4c59', 5)
    heading = {'outro': 'SEE YOU NEXT TIME', 'transition': 'NEXT PHRASE',
               'viewer-turn': 'YOUR TURN — SAY IT ALOUD!', 'phrase': 'SAY IT WITH ME',
               'meaning': 'WHAT IT MEANS', 'example': 'IN A CONVERSATION', 'cue': 'GIVE IT A TRY'}[kind]
    heading_width = draw.textlength(heading, font=font(pos(28), True)) / scale + 58
    box((130, 190, 130 + heading_width, 253), accent, 31)
    label(159, 202, heading, 28, ink, True)
    # Offset card and a narrow coloured spine give the phrase a clear focal point.
    box((148, 318, 1790, 853), '#28444f', theme['cornerRadius'])
    box((130, 300, 1772, 835), theme['card'], theme['cornerRadius'])
    box((130, 346, 141, 788), accent, 5)
    fitted(text, (210, 370, 1478, 390), theme['phraseMaxSize'], 26, ink)
    # Two interlocking speech bubbles: vector artwork, with no external assets.
    if theme['artwork']:
        box((1510, 166, 1620, 239), '#294957', 20)
        line([(1534, 191), (1594, 191)], '#8ddacb', 4)
        line([(1534, 207), (1574, 207)], '#8ddacb', 4)
        draw.polygon([(pos(x), pos(y)) for x, y in [(1528, 232), (1528, 256), (1552, 232)]], fill='#294957')
        box((1635, 202, 1745, 275), accent, 20)
        for x in (1660, 1690, 1720):
            box((x-4, 233, x+4, 241), ink, 4)
        draw.polygon([(pos(x), pos(y)) for x, y in [(1703, 266), (1730, 291), (1730, 266)]], fill=accent)
    # The timer itself is drawn by FFmpeg at y=910; never add a track or numbers.
    title = doc.get('title', 'Phrase Studio')[:100]
    footer_font = font(pos(23))
    while title and draw.textlength(title, font=footer_font) > pos(1660):
        title = title[:-1]
    label(130, 993, title, 23, theme['muted'])
    image.save(path)


def render(root, output, preset='master', transition_sound='none', create_pdf=True, theme_path=None):
    if transition_sound not in ('none', 'whoosh'):
        raise ValueError('Unknown transition sound')
    theme = load_theme(theme_path)
    doc = validate(root)
    metadata = root / 'project.json'
    metadata.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    width, height = (1280, 720) if preset == 'preview' else (1920, 1080)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='render-', dir=root) as tmp:
        work = Path(tmp)
        videos = []
        audios = []
        images = []
        for index, section in enumerate(doc['timeline']):
            emit(status='rendering', progress=round(index / len(doc['timeline']) * 90), message=f"{index + 1}/{len(doc['timeline'])} · {section['type']}")
            frames = section['frames']
            seconds = frames / FPS
            png = work / f'{index}.png'
            video = work / f'{index}.mp4'
            audio = work / f'{index}.wav'
            slide(doc, section, png, width, height, theme)
            images.append(png)
            args = ['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-framerate', FPS, '-i', png]
            if section['type'] == 'viewer-turn':
                x, y, line_width = round(130 * width / 1920), round(910 * height / 1080), round(1660 * width / 1920)
                # A moving colored overlay, masked at the left edge. No background track.
                args += ['-f', 'lavfi', '-i', f'color=c={theme["accent"]}:s={line_width}x6:r={FPS}', '-filter_complex', f"[0:v][1:v]overlay=x='{x}-{line_width}*n/{max(1, frames - 1)}':y={y}:shortest=1,drawbox=x=0:y={y}:w={x}:h=6:color={theme['background']}:t=fill[v]", '-map', '[v]']
                run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', seconds, '-c:a', 'pcm_s16le', audio])
            elif section['type'] in ('transition', 'title'):
                run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', seconds, '-c:a', 'pcm_s16le', audio])
            else:
                run(['ffmpeg', '-v', 'error', '-y', '-ss', section['source']['trimStartSeconds'], '-i', root / section['source']['file'], '-vn', '-af', f'atrim=duration={section["durationSeconds"]},asetpts=PTS-STARTPTS,aformat=channel_layouts=mono,apad,atrim=duration={seconds},asetpts=PTS-STARTPTS', '-ar', 48000, '-ac', 2, '-c:a', 'pcm_s16le', audio])
            args += ['-frames:v', frames, '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-threads', '2', '-pix_fmt', 'yuv420p', '-r', FPS, video]
            run(args)
            videos.append(video)
            audios.append(audio)
        # One PCM stream avoids per-clip AAC priming gaps.
        combined = work / 'narration.wav'
        with wave.open(str(combined), 'wb') as out:
            out.setnchannels(2)
            out.setsampwidth(2)
            out.setframerate(48000)
            for path in audios:
                with wave.open(str(path), 'rb') as source:
                    while chunk := source.readframes(65536):
                        out.writeframesraw(chunk)
        listing = work / 'videos.txt'
        listing.write_text('\n'.join(f"file '{p.name}'" for p in videos), encoding='utf-8')
        temporary = work / 'final.mp4'
        emit(status='rendering', progress=94, message='Mixing narration and validating export')
        mux = ['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '1', '-i', listing]
        if transition_sound == 'whoosh' and any(s['type'] == 'transition' for s in doc['timeline']):
            normalized, effects = work / 'normalized.wav', work / 'effects.wav'
            run(['ffmpeg', '-v', 'error', '-y', '-i', combined, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', 48000, '-ac', 2, '-c:a', 'pcm_s16le', normalized])
            write_effects(doc['timeline'], effects)
            mux += ['-i', normalized, '-i', effects, '-filter_complex', '[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]', '-map', '0:v:0', '-map', '[a]']
        else:
            mux += ['-i', combined, '-map', '0:v:0', '-map', '1:a:0', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11']
        run(mux + ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', 48000, '-ac', 2, '-movflags', '+faststart', temporary])
        info = probe(temporary)
        v = next(s for s in info['streams'] if s['codec_type'] == 'video')
        a = next(s for s in info['streams'] if s['codec_type'] == 'audio')
        if (v['width'], v['height'], v['codec_name'], v['pix_fmt'], v['r_frame_rate']) != (width, height, 'h264', 'yuv420p', '30/1') or a['channels'] != 2 or a['sample_rate'] != '48000' or a['codec_name'] != 'aac' or abs(float(info['format']['duration']) - doc['totalDurationSeconds']) > .15 or abs(float(v['duration']) - float(a['duration'])) > .06:
            raise ValueError('Export validation failed')
        shutil.copyfile(temporary, output)
        pdf_warning = None
        if create_pdf:
            emit(status='rendering', progress=98, message='Creating your slide PDF')
            try:
                slides_pdf(images, output.with_suffix('.pdf'))
            except Exception as error:
                pdf_warning = f'Video ready, but PDF could not be created: {error}'
        output.with_suffix('.report.json').write_text(json.dumps({'preset': preset, 'visualTheme': 'studio-cards-v1', 'theme': theme, 'createPdf': create_pdf, 'pdfWarning': pdf_warning, 'renderFlowVersion': 2, 'pacing': doc['pacing'], 'transitionSound': transition_sound, 'durationSeconds': doc['totalDurationSeconds'], 'timeline': doc['timeline'], 'warnings': doc['warnings'], 'streams': info['streams']}, indent=2), encoding='utf-8')
    emit(status='completed', progress=100, message=pdf_warning or ('Your video and slide PDF are ready' if create_pdf else 'Your video is ready'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['import', 'render', 'health'])
    parser.add_argument('--input', type=Path)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--preset', choices=['preview', 'master'], default='master')
    parser.add_argument('--transition-sound', choices=['none', 'whoosh'], default='none')
    parser.add_argument('--no-pdf', action='store_true')
    parser.add_argument('--theme', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'health':
            missing = [p for p in ('ffmpeg', 'ffprobe') if not shutil.which(p)]
            if missing:
                raise ValueError('Install and add to PATH: ' + ', '.join(missing))
            emit(status='ready', python=sys.version.split()[0])
        elif args.command == 'import':
            doc = import_package(args.input, args.project)
            emit(status='imported', title=doc['title'], warnings=doc['warnings'])
        else:
            render(args.project, args.output, args.preset, args.transition_sound, not args.no_pdf, args.theme)
    except Exception as exc:
        emit(status='failed', error=str(exc))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
