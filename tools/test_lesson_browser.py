"""Browser integration using isolated accounts and mocked audio/AI, not real microphone tests."""
import json
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import profile
import tutor
import app as web
from tools.test_teaching import fixture_script
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
MOCK_SPEECH='''
window.__recognitions=[];
window.SpeechRecognition=class {
 constructor(){window.__recognitions.push(this);}
 start(){this.active=true;}
 stop(){this.active=false;if(this.onend)this.onend();}
 abort(){this.active=false;if(this.onend)this.onend();}
};
window.speechSynthesis.speak=function(u){window.__utterance=u;if(u.onstart)u.onstart();};
window.speechSynthesis.cancel=function(){};
window.speechSynthesis.pause=function(){};
window.speechSynthesis.resume=function(){};
'''

def main():
    with tempfile.TemporaryDirectory() as tmp:
        old=profile.DB_PATH;profile.DB_PATH=Path(tmp)/'browser.db';profile.init_db()
        sid=profile.create_account('Browser fixture','Form 3','browser@example.invalid','Fixture-only-password-83',birth_date='2005-01-01')
        cookie=web.app.session_interface.get_signing_serializer(web.app).dumps({'sid':sid,'_csrf':'browser-csrf'})
        def state(subject,topic,*a,**kw):return ('ready',None,tutor._illustrate_lesson(fixture_script(),subject,topic))
        with patch.object(web,'lesson_state',side_effect=state),patch.object(web,'_prefetch_narration'),patch.object(web.llm,'tts_available',return_value=False),patch.object(web.llm,'PROVIDER','gemini'),patch.object(web.tutor,'ask_question',return_value={'answer':'Volume is measured in cubic units.','points':['Use cm³.']}),patch.object(web.tutor,'grade_drawing',return_value={'correct':True,'error_type':None,'teacher_note':'Drawing received and checked.'}):
            server=make_server('127.0.0.1',0,web.app,threaded=True);threading.Thread(target=server.serve_forever,daemon=True).start()
            base=f'http://127.0.0.1:{server.server_port}'
            try:
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
                    for width in (1280,390):
                        context=browser.new_context(viewport={'width':width,'height':900},has_touch=True,reduced_motion='reduce')
                        context.add_cookies([{'name':'session','value':cookie,'url':base}]);context.add_init_script(MOCK_SPEECH)
                        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                        before=profile.DB_PATH.read_bytes()
                        page.goto(base+'/lesson/mathematics/volume_area');page.wait_for_function('!!plan && !!beats.length')
                        assert page.locator('.learning-profile,#keyword-listen,#lesson-explore').count()==0
                        assert page.evaluate('window.__recognitions.length')==1
                        assert page.evaluate('SPEEDS.normal')==1.25
                        assert page.evaluate('lesson.steps.some(o=>o.name==="cuboid3d")')
                        assert page.evaluate('beats.length===lesson.steps.filter(o=>o.op==="say").length')
                        page.evaluate('seekTo(plan.scenes[0].t1-.01,false)')
                        assert '24 cm³' in page.locator('#board').text_content()
                        page.screenshot(path=f'/workspace/work/player-{width}.png',full_page=True)
                        page.evaluate('''() => { const r=window.__recognitions.at(-1); r.onresult({resultIndex:0,results:[[{transcript:"Hey tutor why cubic units"}]]}); }''')
                        assert page.locator('#ask-input').input_value()=='why cubic units'
                        assert not page.evaluate('playing')
                        page.evaluate('''() => { const r=window.__recognitions.at(-1); const result=[{transcript:"Hey tutor why cubic units"}];result.isFinal=true;r.onresult({resultIndex:0,results:[result]}); }''')
                        page.locator('#tc-resume').click();assert page.evaluate('playing && keywordEnabled')
                        assert page.evaluate('window.__recognitions.length')==2
                        # Browser ending a recognition session restarts automatically.
                        page.evaluate('window.__recognitions.at(-1).onend()');page.wait_for_timeout(900)
                        assert page.evaluate('window.__recognitions.length')==3
                        # A denied microphone does not cause repeated prompts.
                        page.evaluate('window.__recognitions.at(-1).onerror({error:"not-allowed"})');page.locator('#btn-playpause').click()
                        assert page.evaluate('window.__recognitions.length')==3
                        assert profile.DB_PATH.read_bytes()==before
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        page.goto(base+'/lesson/computer/hardware');page.wait_for_function('!!plan')
                        page.evaluate('seekTo(plan.scenes[0].t1-.01,false)')
                        assert 'CPU' in page.locator('#board').text_content()
                        assert not page.evaluate('lesson.steps.some(o=>["graph_axes","cuboid3d","vector3d"].includes(o.name))')
                        page.screenshot(path=f'/workspace/work/hardware-{width}.png',full_page=True)
                        # Calculator and real image submission from the pointer pad.
                        page.goto(base+'/exam/physics/pressure');page.locator('.answer-canvas').wait_for()
                        page.locator('.exam-calculator summary').click();page.locator('.calc-expression').fill('12 × sin(30)');page.locator('.calc-expression').press('Enter')
                        assert page.locator('.exam-calculator output').inner_text()=='6'
                        canvas=page.locator('.answer-canvas');canvas.scroll_into_view_if_needed();box=canvas.bounding_box()
                        page.locator('[data-tool="line"]').click()
                        page.mouse.move(box['x']+30,box['y']+30);page.mouse.down();page.mouse.move(box['x']+120,box['y']+70,steps=5);page.mouse.up()
                        page.wait_for_timeout(600)
                        assert page.evaluate('draft.answers[0].strokes.length')==1
                        page.reload();page.locator('.answer-canvas').wait_for()
                        assert page.evaluate('draft.answers[0].strokes.length')==1
                        page.locator('[data-tool="undo"]').click();assert page.evaluate('!draft.answers[0]')
                        page.locator('[data-tool="pen"]').click()
                        canvas=page.locator('.answer-canvas');canvas.scroll_into_view_if_needed();box=canvas.bounding_box()
                        # Touch pointer drawing uses the same coordinate conversion as mouse/stylus.
                        cdp=context.new_cdp_session(page)
                        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':box['x']+25,'y':box['y']+25}]})
                        cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':box['x']+90,'y':box['y']+70}]})
                        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
                        cdp.detach()
                        page.locator('.ans-work').fill('P = F/A = 120/0.03');page.locator('.ans-final').fill('4000 Pa')
                        page.screenshot(path=f'/workspace/work/exam-{width}.png',full_page=True)
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        assert page.evaluate('!!draft.answers[0].image')
                        page.locator('#btn-submit').click();page.wait_for_url('**/results/*');page.locator('.result-row').wait_for()
                        assert page.locator('.submitted-drawing').count()==1
                        assert 'Drawing received' in page.locator('.result-row').inner_text()
                        page.goto(base+'/exam/physics/heat_transfer');assert page.locator('.answer-canvas').count()==0
                        assert page.locator('textarea').count()==1
                        page.goto(base+'/exam/mathematics/numbers');assert page.locator('.answer-canvas').count()==1
                        page.goto(base+'/exam/computer/hardware');assert page.locator('.exam-calculator,.answer-canvas').count()==0
                        assert not errors,errors
                        print(f'PASS {width}px: automatic recognition/resume/denial, inline 3D, hardware diagram, calculator, drawing persistence/submission, theory unchanged')
                        context.close()
                    browser.close()
            finally:server.shutdown();profile.DB_PATH=old

if __name__=='__main__':main()
