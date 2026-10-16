"""Smoke-test the packaged Windows UI in the runner's installed Microsoft Edge."""
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
import test_engine


def main():
    from playwright.sync_api import sync_playwright, expect
    fixture = test_engine.EngineTest
    fixture.setUpClass()
    executable = Path(sys.argv[1]).resolve()
    env = {**os.environ, 'PHRASE_DATA':str(fixture.base/'browser-data'), 'PHRASE_OPEN_BROWSER':'0', 'PHRASE_PYTHON':sys.executable}
    process = subprocess.Popen([str(executable)], cwd=executable.parent, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+30
        while True:
            try:
                with urlopen('http://127.0.0.1:5278/api/health',timeout=5) as response: response.read()
                break
            except OSError:
                if time.monotonic()>deadline:raise
                time.sleep(.2)
        package=fixture('test_text_fitting_and_safe_paths').package('browser')
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1080})
            errors=[]
            page.on('pageerror',lambda error: errors.append(str(error)))
            page.goto('http://127.0.0.1:5278')
            expect(page.locator('#notice')).to_contain_text('Ready to render',timeout=30000)
            page.locator('#package').set_input_files(package)
            page.get_by_role('button',name='Import recording',exact=True).click()
            expect(page.locator('#title')).to_have_text('Work life',timeout=30000)
            page.locator('#preset').select_option('preview')
            page.get_by_label('Soft whoosh between phrases').check()
            page.get_by_role('button',name='Generate video',exact=True).click()
            expect(page.locator('#result')).to_be_visible(timeout=90000)
            expect(page.locator('#video')).to_have_attribute('data-ready','true',timeout=30000)
            with page.expect_download() as downloaded:
                page.get_by_role('link',name='Save video',exact=True).click()
            assert downloaded.value.suggested_filename.endswith('.mp4')
            page.reload()
            expect(page.locator('#title')).to_have_text('Work life')
            expect(page.get_by_label('Soft whoosh between phrases')).to_be_checked()
            expect(page.locator('#result')).to_be_visible()
            assert not errors,errors
            target=Path('artifacts/ui-smoke.png');target.parent.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(target),full_page=True)
            browser.close()
        print('Windows Edge smoke passed: import, generate, playable video, download, restore')
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
        fixture.tearDownClass()


if __name__=='__main__':main()
