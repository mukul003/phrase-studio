import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from PIL import Image

APP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('studio', APP / 'engine/studio.py')
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


class EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        subprocess.run(['node', str(APP / 'tests/make-session.cjs'), str(cls.base / 'session.json')], check=True)
        cls.doc = json.loads((cls.base / 'session.json').read_text())
        cls.audio = cls.base / 'tone.webm'
        studio.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.2', '-c:a', 'libopus', cls.audio])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def package(self, name, doc=None, extras=None, missing=False):
        path = self.base / (name + '.zip')
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('session.json', json.dumps(doc or self.doc))
            for s in self.doc['timeline']:
                if s['type'] != 'viewer-turn' and not missing:
                    z.write(self.audio, s['source']['file'])
            for key, value in (extras or {}).items():
                z.writestr(key, value)
        return path

    def test_real_core_export_import_and_master_render(self):
        root = self.base / 'complete'
        doc = studio.import_package(self.package('good'), root)
        self.assertEqual(len([s for s in doc['timeline'] if s['type'] == 'viewer-turn']), 1)
        self.assertTrue((root / 'original-package.zip').is_file())
        output = root / 'result.mp4'
        studio.render(root, output)
        info = studio.probe(output)
        video = next(s for s in info['streams'] if s['codec_type'] == 'video')
        self.assertEqual((video['width'], video['height']), (1920, 1080))
        self.assertAlmostEqual(float(info['format']['duration']), doc['totalDurationSeconds'], delta=.1)
        viewer = next(s for s in doc['timeline'] if s['type'] == 'viewer-turn')
        widths = []
        for number, fraction in enumerate((.05, .5, .95)):
            image_path = root / f'bar-{number}.png'
            studio.run(['ffmpeg', '-v', 'error', '-y', '-ss', viewer['startSeconds'] + (viewer['endSeconds']-viewer['startSeconds'])*fraction, '-i', output, '-frames:v', 1, image_path])
            with Image.open(image_path) as im:
                pixels = im.convert('RGB')
                widths.append(sum(1 for x in range(130, 1790) if (lambda c:c[0]>150 and c[1]>100 and c[2]<150)(pixels.getpixel((x, 912)))))
        self.assertGreater(widths[0], 1400)
        self.assertTrue(widths[0] > widths[1] > widths[2], widths)
        self.assertLess(widths[2], 170)
        # Viewer audio is silent, and narration is duplicated equally into both channels.
        wav = root / 'output.wav'
        studio.run(['ffmpeg', '-v', 'error', '-y', '-i', output, '-c:a', 'pcm_s16le', wav])
        import array, wave
        with wave.open(str(wav), 'rb') as w:
            w.setpos(round((viewer['startSeconds']+.1)*48000))
            samples = array.array('h', w.readframes(round(.7*48000)))
            self.assertLess(max(abs(s) for s in samples), 20)
        self.assertEqual(doc['timeline'][0]['type'], 'intro')
        self.assertEqual(doc['timeline'][-1]['type'], 'outro')
        # Preserve QA frames outside TemporaryDirectory when explicitly requested.
        import os, shutil
        if os.environ.get('PHRASE_QA_OUTPUT'):
            target = Path(os.environ['PHRASE_QA_OUTPUT']);target.mkdir(parents=True, exist_ok=True)
            for file in [output, *root.glob('bar-*.png')]: shutil.copy2(file, target / file.name)

    def test_rejects_traversal_and_removes_partial_import(self):
        root = self.base / 'unsafe'
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            studio.import_package(self.package('unsafe', extras={'../escaped.txt':'oops'}), root)
        self.assertFalse(root.exists())
        self.assertFalse((self.base / 'escaped.txt').exists())

    def test_rejects_missing_audio_draft_external_and_bad_order(self):
        cases = []
        draft = copy.deepcopy(self.doc);draft['renderReady']=False;cases.append(draft)
        external = copy.deepcopy(self.doc);external['source']='voice-memos';cases.append(external)
        order = copy.deepcopy(self.doc);order['timeline'].reverse();cases.append(order)
        for i, doc in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(ValueError):
                studio.import_package(self.package(f'bad-{i}', doc), self.base / f'bad-{i}')
        with self.assertRaisesRegex(ValueError, 'Missing recording'):
            studio.import_package(self.package('missing', missing=True), self.base / 'missing')

    def test_viewer_timing_is_measured_phrase_average_and_override(self):
        root = self.base / 'timing'
        doc = studio.import_package(self.package('timing'), root)
        viewer = next(s for s in doc['timeline'] if s['type']=='viewer-turn')
        phrase_times = [s['durationSeconds'] for s in doc['timeline'] if s['type']=='phrase']
        self.assertAlmostEqual(viewer['durationSeconds'], sum(phrase_times)/len(phrase_times)+1)
        original = json.loads((root/'session.json').read_text())
        original['lesson']['phrases'][0]['practiceSeconds']=4
        (root/'session.json').write_text(json.dumps(original))
        viewer = next(s for s in studio.validate(root)['timeline'] if s['type']=='viewer-turn')
        self.assertEqual(viewer['durationSeconds'], 4)

    def test_edge_trimming_keeps_internal_pauses_and_rejects_silent_take(self):
        import array, math, wave
        rate = 48000
        path = self.base / 'quiet-edges.wav'
        samples = array.array('h')
        for seconds, voiced in [(1, False), (.4, True), (.5, False), (.4, True), (2, False)]:
            samples.extend(round(10000*math.sin(2*math.pi*440*i/rate)) if voiced else 0 for i in range(round(seconds*rate)))
        with wave.open(str(path), 'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(samples.tobytes())
        start, end = studio.audio_window(path, studio.duration(path))
        self.assertAlmostEqual(start, .9, delta=.02)
        self.assertAlmostEqual(end, 2.4, delta=.02)
        self.assertAlmostEqual(end-start, 1.5, delta=.03)
        silent = self.base / 'silent.wav'
        studio.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t','1',silent])
        with self.assertRaisesRegex(ValueError,'silent'):
            studio.audio_window(silent, 1)

    def test_text_fitting_and_safe_paths(self):
        for text in ['../x', '/x', 'C:/x', 'clips\\x']:
            self.assertFalse(studio.safe_member(text))
        self.assertTrue(studio.safe_member('clips/p0001-phrase.webm'))
        doc=copy.deepcopy(self.doc)
        section={'id':'long','type':'meaning','text':'long text '*3000}
        with self.assertRaisesRegex(ValueError, 'too much text'):
            studio.slide(doc,section,self.base/'oversize.png',1280,720)

if __name__ == '__main__':
    unittest.main()
