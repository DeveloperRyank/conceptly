"""Headless Chrome integration: fixture lessons, real auth/CSRF, isolated profile DB.

Does not prove audible speech, real-device performance or live LLM output quality.
Run with requirements.txt plus playwright and an installed Chromium.
"""
import json
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import profile
import app as web
from tools.test_teaching import fixture_script
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

MOCK_SPEECH='''
window.__recognitions = [];
window.SpeechRecognition = class {
 constructor(){ window.__recognitions.push(this); }
 start(){ this.active=true; }
 stop(){ this.active=false; if(this.onend)this.onend(); }
 abort(){ this.active=false; if(this.onend)this.onend(); }
};
window.speechSynthesis.speak = function(u){ window.__utterance=u; if(u.onstart)u.onstart(); };
window.speechSynthesis.cancel = function(){};
window.speechSynthesis.pause = function(){};
window.speechSynthesis.resume = function(){};
'''

def main():
    with tempfile.TemporaryDirectory() as tmp:
        old=profile.DB_PATH;profile.DB_PATH=Path(tmp)/'browser.db';profile.init_db()
        sid=profile.create_account('Browser fixture','Form 3','browser@example.invalid','Fixture-only-password-83',birth_date='2005-01-01')
        profile.record_answer('mathematics','volume_area',False,question='Find the volume of a 4 by 3 by 2 cm cuboid.',answer='24 cm²',feedback='Volume uses cubic units: 24 cm³.',sid=sid)
        cookie=web.app.session_interface.get_signing_serializer(web.app).dumps({'sid':sid,'_csrf':'browser-csrf'})
        script=fixture_script()
        with patch.object(web,'lesson_state',return_value=('ready',None,script)),patch.object(web,'_prefetch_narration'),patch.object(web.llm,'tts_available',return_value=False),patch.object(web.tutor,'ask_question',return_value={'answer':'Volume is length times width times height, measured in cubic units.','points':['Use cm³ for volume.']}):
            server=make_server('127.0.0.1',0,web.app,threaded=True)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{server.server_port}'
            try:
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
                    for width in (1280,390):
                        context=browser.new_context(viewport={'width':width,'height':900})
                        context.add_cookies([{'name':'session','value':cookie,'url':base}]);context.add_init_script(MOCK_SPEECH)
                        page=context.new_page();errors=[];writes=[]
                        page.on('pageerror',lambda e:errors.append(str(e)))
                        page.on('request',lambda r: writes.append(r.url) if r.method=='POST' else None)
                        before=profile.DB_PATH.read_bytes()
                        page.goto(base+'/lesson/mathematics/volume_area');page.wait_for_function('!!plan && !!beats.length')
                        # All narration survives planning, including say operations with no following write.
                        assert page.evaluate('beats.length === lesson.steps.filter(o => o.op === "say").length')
                        page.locator('.learning-profile summary').click()
                        assert '24 cm²' in page.locator('.learning-profile').inner_text()
                        assert 'Volume uses cubic units' in page.locator('.learning-profile').inner_text()
                        # The opt-in recogniser is not created before the student enables it.
                        assert page.evaluate('window.__recognitions.length')==0
                        page.locator('#keyword-listen').click()
                        assert page.locator('#keyword-listen').get_attribute('aria-pressed')=='true'
                        page.evaluate('''() => { const r=window.__recognitions[0]; r.onresult({resultIndex:0,results:[[{transcript:"Hey tutor why cubic units"}]]}); }''')
                        assert page.locator('#ask-panel').evaluate('e=>e.classList.contains("open")')
                        assert page.locator('#ask-input').input_value()=='why cubic units'
                        assert not page.evaluate('playing')
                        assert page.locator('#keyword-listen').get_attribute('aria-pressed')=='true'
                        # Final recognition completes the question naturally and submits once.
                        page.evaluate('''() => { const r=window.__recognitions[0]; const result=[{transcript:"Hey tutor why cubic units"}]; result.isFinal=true; r.onresult({resultIndex:0,results:[result]}); }''')
                        page.locator('#tc-resume').wait_for()
                        assert page.locator('#keyword-listen').get_attribute('aria-pressed')=='false'
                        assert not page.evaluate('playing')
                        page.locator('#tc-resume').click();assert page.evaluate('playing')
                        # 3D controls pause the lesson, update real dimensions, and require explicit resume.
                        page.locator('#explore-toggle').click();assert not page.evaluate('playing')
                        assert page.locator('#explore-panel').is_visible()
                        page.locator('#explore-parameter').fill('4');page.locator('#explore-parameter').dispatch_event('input')
                        assert '48.0 cm³' in page.locator('#explore-output').inner_text()
                        page.locator('#explore-angle').fill('100');page.locator('#explore-angle').dispatch_event('input')
                        assert page.locator('#explore-svg line').count()==12
                        page.locator('#explore-motion').click()
                        page.wait_for_timeout(100)
                        assert page.locator('#explore-motion').get_attribute('aria-pressed')=='true'
                        page.screenshot(path=f'/workspace/work/model-{width}.png',full_page=True)
                        page.locator('#explore-resume').click();assert page.evaluate('playing')
                        assert not page.locator('#explore-panel').is_visible()
                        page.screenshot(path=f'/workspace/work/lesson-{width}.png',full_page=True)
                        # No new layout overflow, no profile writes, and an authenticated ask is the only POST.
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                        assert profile.DB_PATH.read_bytes()==before
                        assert all(url.endswith('/api/ask') for url in writes),writes
                        assert not errors,errors
                        print(f'PASS {width}px: profile, keyword, ask/resume, 3D, no profile writes or browser errors')
                        context.close()
                    # Reduced motion keeps manual rotation and prevents automatic animation.
                    context=browser.new_context(viewport={'width':390,'height':900},reduced_motion='reduce')
                    context.add_cookies([{'name':'session','value':cookie,'url':base}]);context.add_init_script(MOCK_SPEECH)
                    page=context.new_page();page.goto(base+'/lesson/chemistry/chemical_bonding');page.wait_for_function('!!plan')
                    page.locator('#explore-toggle').click();assert page.locator('#explore-motion').is_disabled()
                    assert '109.5' in page.locator('#explore-output').inner_text()
                    context.close()
                    print('PASS reduced motion: manual model available, animation disabled')
                    for subject,topic,expected in [('chemistry','separation_techniques','salt'),('physics','current_electricity','Switch'),('computer','hardware','CPU')]:
                        context=browser.new_context(viewport={'width':390,'height':900})
                        context.add_cookies([{'name':'session','value':cookie,'url':base}]);context.add_init_script(MOCK_SPEECH)
                        page=context.new_page();page.goto(base+f'/lesson/{subject}/{topic}');page.wait_for_function('!!plan')
                        page.locator('#explore-toggle').click()
                        if topic in ('separation_techniques','current_electricity'):
                            page.locator('#explore-parameter').fill('1');page.locator('#explore-parameter').dispatch_event('input')
                        assert expected.lower() in page.locator('#explore-output').inner_text().lower()
                        context.close()
                    browser.close()
                    print('PASS apparatus and data-flow models: distillation, closed circuit, computer')
            finally:server.shutdown();profile.DB_PATH=old

if __name__=='__main__':main()
