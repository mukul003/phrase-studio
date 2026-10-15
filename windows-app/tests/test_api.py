"""Exercise the real ASP.NET host. Requires a built executable (CI runs on Windows)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import test_engine

BASE = 'http://127.0.0.1:5278'


def api(path, data=None, content_type='application/json', origin=None):
    headers = {'X-Phrase-Studio':'local'}
    if data is not None:
        headers['Content-Type'] = content_type
    if origin:
        headers['Origin'] = origin
    with urlopen(Request(BASE+path, data=data, headers=headers), timeout=30) as response:
        body = response.read()
        return json.loads(body) if response.headers.get('Content-Type','').startswith('application/json') else body


def wait_job(pid):
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        job=api('/api/projects/'+pid+'/job')
        if job and job['status']!='rendering': return job
        time.sleep(.2)
    raise AssertionError('Render timed out')


def main():
    EngineTest = test_engine.EngineTest
    executable=Path(sys.argv[1]).resolve()
    EngineTest.setUpClass()
    process=None
    try:
        env={**os.environ,'PHRASE_DATA':str(EngineTest.base/'app-data'),'PHRASE_OPEN_BROWSER':'0'}
        # The source engine is used before packaging; bundled engine is used on the second CI pass.
        env['PHRASE_PYTHON']=sys.executable
        process=subprocess.Popen([str(executable)],cwd=executable.parent,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        deadline=time.monotonic()+30
        while True:
            try: health=api('/api/health');break
            except OSError:
                if process.poll() is not None: raise RuntimeError(process.stderr.read().decode())
                if time.monotonic()>deadline:raise
                time.sleep(.2)
        assert health['ready'],health
        try:api('/api/settings',b'{"preset":"preview"}',origin='https://example.com')
        except HTTPError as error:assert error.code==403
        else:raise AssertionError('Cross-origin mutation allowed')
        api('/api/settings',b'{"preset":"preview"}')
        assert api('/api/settings')['preset']=='preview'
        fixture=EngineTest('test_text_fitting_and_safe_paths')
        package=fixture.package('api')
        boundary='PhraseStudioTestBoundary'
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="package"; filename="recording.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode()+package.read_bytes()+f'\r\n--{boundary}--\r\n'.encode())
        pid=api('/api/projects',body,'multipart/form-data; boundary='+boundary)['id']
        assert api('/api/projects/'+pid)['title']=='Work life'
        assert any(p['id']==pid for p in api('/api/projects'))
        api('/api/projects/'+pid+'/render',b'{"preset":"preview"}')
        job=wait_job(pid)
        assert job['status']=='completed',job
        video=api(job['download'])
        assert b'ftyp' in video[:64]
        assert api('/api/projects/'+pid+'/job')['download']==job['download']
        job=api('/api/projects/'+pid+'/render',b'{"preset":"master"}')
        api('/api/jobs/'+job['id']+'/cancel',b'')
        job=wait_job(pid)
        assert job['status']=='cancelled',job
        print('API smoke passed: import, health, settings, origin guard, render, download, cancel')
    finally:
        if process:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        EngineTest.tearDownClass()


if __name__=='__main__':main()
