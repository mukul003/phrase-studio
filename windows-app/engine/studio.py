"""Local Phrase Studio media engine. No network calls; imported originals are immutable."""
import argparse
from functools import lru_cache
import json
import math
import os
import re
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
    doc['totalDurationSeconds'] = at / FPS
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
def font(size):
    for candidate in [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/segoeui.ttf', Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]:
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


def slide(doc, section, path, width, height):
    if len(section.get('text', '')) > 6000:
        raise ValueError(f"Section {section['id']} has too much text for one slide")
    image = Image.new('RGB', (width, height), BG)
    draw = ImageDraw.Draw(image)
    scale = width / 1920
    def pos(n): return round(n * scale)
    draw.text((pos(130), pos(65)), 'FLUENT ENGLISH FOR YOU', font=font(pos(28)), fill=ACCENT)
    title = doc.get('title', 'Phrase Studio')[:100]
    heading = {'intro': 'LET’S GET STARTED', 'outro': 'SEE YOU NEXT TIME', 'viewer-turn': 'YOUR TURN — SAY IT ALOUD!', 'phrase': 'SAY IT WITH ME', 'meaning': 'WHAT IT MEANS', 'example': 'IN A CONVERSATION', 'cue': 'GIVE IT A TRY'}[section['type']]
    draw.text((pos(130), pos(210)), heading, font=font(pos(30)), fill=ACCENT)
    max_width = pos(1660)
    for size in range(86, 25, -2):
        f = font(pos(size))
        lines = wrapped(draw, section.get('text', ''), f, max_width)
        spacing = pos(size * 1.45)
        if len(lines) * spacing <= pos(490):
            break
    else:
        raise ValueError(f"Section {section['id']} has too much text for one slide")
    y = pos(340) + max(0, (pos(490) - len(lines) * spacing) // 2)
    for line in lines:
        draw.text((pos(130), y), line, font=f, fill=FG)
        y += spacing
    draw.text((pos(130), pos(994)), title, font=font(pos(24)), fill='#93a9b9')
    image.save(path)


def render(root, output, preset='master'):
    doc = validate(root)
    width, height = (1280, 720) if preset == 'preview' else (1920, 1080)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='render-', dir=root) as tmp:
        work = Path(tmp)
        videos = []
        audios = []
        for index, section in enumerate(doc['timeline']):
            emit(status='rendering', progress=round(index / len(doc['timeline']) * 90), message=f"{index + 1}/{len(doc['timeline'])} · {section['type']}")
            frames = section['frames']
            seconds = frames / FPS
            png = work / f'{index}.png'
            video = work / f'{index}.mp4'
            audio = work / f'{index}.wav'
            slide(doc, section, png, width, height)
            args = ['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-framerate', FPS, '-i', png]
            if section['type'] == 'viewer-turn':
                x, y, line_width = round(130 * width / 1920), round(910 * height / 1080), round(1660 * width / 1920)
                # A moving colored overlay, masked at the left edge. No background track.
                args += ['-f', 'lavfi', '-i', f'color=c={ACCENT}:s={line_width}x6:r={FPS}', '-filter_complex', f"[0:v][1:v]overlay=x='{x}-{line_width}*n/{max(1, frames - 1)}':y={y}:shortest=1,drawbox=x=0:y={y}:w={x}:h=6:color={BG}:t=fill[v]", '-map', '[v]']
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
        run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '1', '-i', listing, '-i', combined, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-ar', 48000, '-ac', 2, '-movflags', '+faststart', temporary])
        info = probe(temporary)
        v = next(s for s in info['streams'] if s['codec_type'] == 'video')
        a = next(s for s in info['streams'] if s['codec_type'] == 'audio')
        if (v['width'], v['height'], v['codec_name'], v['pix_fmt'], v['r_frame_rate']) != (width, height, 'h264', 'yuv420p', '30/1') or a['channels'] != 2 or a['sample_rate'] != '48000' or a['codec_name'] != 'aac' or abs(float(info['format']['duration']) - doc['totalDurationSeconds']) > .15 or abs(float(v['duration']) - float(a['duration'])) > .06:
            raise ValueError('Export validation failed')
        shutil.copyfile(temporary, output)
        output.with_suffix('.report.json').write_text(json.dumps({'preset': preset, 'durationSeconds': doc['totalDurationSeconds'], 'warnings': doc['warnings'], 'streams': info['streams']}, indent=2), encoding='utf-8')
    emit(status='completed', progress=100, message='Your video is ready')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['import', 'render', 'health'])
    parser.add_argument('--input', type=Path)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--preset', choices=['preview', 'master'], default='master')
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
            render(args.project, args.output, args.preset)
    except Exception as exc:
        emit(status='failed', error=str(exc))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
