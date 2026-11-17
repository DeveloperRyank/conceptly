"""Teaching integration checks. All profile writes go to a temporary database."""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import profile
import classifier
import curriculum
import notes
import tutor
import app as web


def fixture_script():
    steps=[]
    narration=("We choose a method from the given conditions, explain each operation, and keep units with the result. "
               "Substitution into the original relationship checks the result independently and exposes a sign error. "
               "Changing a condition can change the method, so identify the assumption before reusing the calculation. ")
    for i in range(16):
        steps.append({'op':'caption','text':f'Worked example {i+1}' if i<4 else f'Concept {i+1}',
                      **({'section':'example'} if i<4 else {'section':'recap'} if i==15 else {})})
        steps.append({'op':'say','text':narration*2})
        steps.append({'op':'write','id':'question','text':'Calculate the value of 2 + 3.'})
        steps.append({'op':'write','id':'answer','text':'2 + 3 = 5'})
    return tutor.normalize_script({'title':'Fixture only','steps':steps},subject='mathematics')


class TeachingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.old=profile.DB_PATH
        profile.DB_PATH=Path(cls.tmp.name)/'fixture.db';profile.init_db()
        cls.a=profile.create_account('Fixture A','Form 3','fixture-a@example.invalid','Fixture-only-password-83',birth_date='2005-01-01')
        cls.b=profile.create_account('Fixture B','Form 3','fixture-b@example.invalid','Fixture-only-password-83',birth_date='2005-01-01')
        web.app.config['TESTING']=True
    @classmethod
    def tearDownClass(cls):
        profile.set_current(None);profile.DB_PATH=cls.old;cls.tmp.cleanup()
    def setUp(self):
        self.client=web.app.test_client()
        with self.client.session_transaction() as session:session['sid']=self.a;session['_csrf']='fixture-csrf'
    def record(self,question='fixture question',answer='wrong answer',feedback='Use units',sid=None,topic='numbers',correct=False):
        profile.record_answer('mathematics',topic,correct,question=question,answer=answer,feedback=feedback,sid=sid or self.a)
    def test_01_banks_unlock_all_existing_topics(self):
        for subject in ('chemistry','computer','mathematics'):
            for topic in curriculum.topics(subject):
                self.assertTrue(web.topic_ready(subject,topic['slug']))
                self.assertGreaterEqual(len(classifier.questions_for_topic(subject,topic['slug'])),3)
    def test_02_generated_files_reproducible(self):
        subprocess.run([sys.executable,str(ROOT/'tools/build_teaching_content.py'),'--check'],check=True)
    def test_03_legacy_rows_preserved_in_order(self):
        with (ROOT/'data/questions.csv').open() as f:legacy=list(csv.DictReader(f))
        with (ROOT/'data/chemistry/questions.csv').open() as f:current=list(csv.DictReader(f))
        for old,new in zip(legacy,current):
            self.assertEqual(old,{k:new[k] for k in old})
    def test_04_no_nan_mcq_keys(self):
        for subject in ('chemistry','computer','mathematics'):
            for row in classifier.questions_for_topic(subject,curriculum.topics(subject)[0]['slug']):
                self.assertIsNone(row['key']);self.assertIsNone(row['concept']);self.assertEqual(row['options'],[])
    def test_05_evidence_isolated(self):
        self.record(question='isolation',sid=self.b)
        self.assertNotIn('isolation',[r['question'] for r in profile.lesson_evidence('mathematics','numbers',self.a,10)])
        self.assertEqual(profile.lesson_evidence('chemistry','numbers',self.b),[])
    def test_06_later_attempt_supersedes(self):
        self.record(question='superseded');self.record(question='superseded',correct=True)
        self.assertNotIn('superseded',[r['question'] for r in profile.lesson_evidence('mathematics','numbers',self.a,10)])
    def test_07_empty_feedback_excluded(self):
        self.record(question='no-feedback',feedback=' ')
        self.assertNotIn('no-feedback',[r['question'] for r in profile.lesson_evidence('mathematics','numbers',self.a,10)])
    def test_08_feedback_invalidates_signature(self):
        self.record(question='signature')
        a=profile.topic_signature('mathematics','numbers',self.a)
        with profile._conn() as c:c.execute('UPDATE history SET feedback = ? WHERE student_id = ? AND question = ?',('Changed feedback',self.a,'signature'))
        self.assertNotEqual(a,profile.topic_signature('mathematics','numbers',self.a))
    def test_09_reference_changes_fingerprint(self):
        old=classifier.topic_fingerprint('mathematics','numbers')
        frame=classifier.load_subject('mathematics');idx=frame.index[0];value=frame.at[idx,'reference_answer']
        try:
            frame.at[idx,'reference_answer']='Changed reference'
            self.assertNotEqual(old,classifier.topic_fingerprint('mathematics','numbers'))
        finally:frame.at[idx,'reference_answer']=value
    def test_10_exam_never_contains_reference(self):
        row=classifier.questions_for_topic('mathematics','numbers')[0]
        resp=self.client.get('/exam/mathematics/numbers')
        self.assertEqual(resp.status_code,200);self.assertNotIn(row['reference_answer'].encode(),resp.data)
        self.assertNotIn(b'reference_answer',resp.data)
    def test_11_written_reference_resolved_server_side(self):
        row=classifier.questions_for_topic('mathematics','numbers')[0]
        r=self.client.post('/api/submit_test',json={'subject':'mathematics','topic':'numbers','answers':[{'uid':row['uid'],'answer':'17','reference_answer':'MALICIOUS'}]},headers={'X-CSRF-Token':'fixture-csrf'})
        self.assertEqual(r.status_code,200)
        job=profile.get_grading_job(r.json['job_id'],self.a)
        with patch.object(tutor,'grade_answers',return_value=[{'correct':True,'error_type':None,'teacher_note':'Checked'}]) as grade:
            web.run_grading(job['id'],self.a,'mathematics','numbers',job['payload'])
            self.assertEqual(grade.call_args.args[2][0]['reference_answer'],row['reference_answer'])
    def test_12_grader_receives_reference(self):
        with patch.object(tutor.llm,'chat_json',return_value={'correct':True,'teacher_note':'Checked'}) as chat:
            tutor.grade_answer('mathematics','numbers','2+3','5','five')
            self.assertIn('five',chat.call_args.args[1])
    def test_13_long_narration_preserved(self):
        text=' '.join(f'word{i}' for i in range(180))
        script=tutor.normalize_script({'steps':[{'op':'caption','text':'Long'},{'op':'say','text':text},{'op':'write','text':'Board line'}]})
        spoken=' '.join(o['text'] for o in script['steps'] if o['op']=='say')
        for word in text.split():self.assertIn(word,spoken)
        self.assertGreater(sum(o['op']=='say' for o in script['steps']),1)
    def test_14_no_sheet_thinning(self):
        script=fixture_script();normal=tutor.normalize_script(script,max_sheets=5)
        self.assertEqual(sum(o['op']=='caption' for o in normal['steps']),16)
    def test_15_depth_rejects_short_lessons(self):
        self.assertTrue(tutor.lesson_depth_problems({'steps':[]}))
    def test_16_fixture_depth_and_structural_contract(self):
        script=fixture_script()
        self.assertEqual(tutor.validate_script(script,subject='mathematics'),[])
        self.assertEqual(tutor.lesson_depth_problems(script),[])
    def test_17_generation_retries_inadequate_depth(self):
        with patch.object(tutor,'_generate_lesson_draft',side_effect=[json.dumps({'steps':[]}),json.dumps(fixture_script())]) as chat,patch.object(tutor,'speech_durations',return_value={}):
            result=tutor.generate_lesson('mathematics','numbers',[],'No history')
            self.assertEqual(chat.call_count,2);self.assertEqual(tutor.lesson_depth_problems(result),[])
            self.assertIn('charge-averaged VOLTAGE',' '.join(chat.call_args.args[0].split()))
    def test_18_recall_uses_actual_saved_text(self):
        evidence=[{'question':'Calculate charge for 20 µF at 12 V.','answer':'240 C','feedback':'Convert microfarads to farads.'}]
        with patch.object(tutor,'_generate_lesson_draft',return_value=json.dumps(fixture_script())),patch.object(tutor,'speech_durations',return_value={}):
            result=tutor.generate_lesson('mathematics','numbers',[],'',evidence=evidence)
            text=json.dumps(result,ensure_ascii=False)
            for row in evidence:
                for value in row.values():self.assertIn(value,text)
            self.assertEqual(tutor.validate_script(result,subject='mathematics'),[])
    def test_19_profile_ui_escapes_evidence_and_caches_by_revision(self):
        self.record(question='<script>unsafe()</script>',feedback='<b>feedback</b>')
        with patch.object(web,'lesson_state',return_value=('ready',None,fixture_script())),patch.object(web,'_prefetch_narration'):
            response=self.client.get('/lesson/mathematics/numbers')
            self.assertEqual(response.status_code,200)
            self.assertIn(b'Your learning profile',response.data);self.assertIn(b'LESSON_REVISION',response.data)
            self.assertNotIn(b'<script>unsafe()</script>',response.data)
            self.assertIn(b'&lt;script&gt;',response.data)
    def test_20_csrf_and_auth_unchanged(self):
        self.assertEqual(self.client.post('/api/ask',json={'question':'why'}).status_code,400)
        self.assertEqual(web.app.test_client().get('/api/lesson/mathematics/numbers/data').status_code,401)
    def test_21_capacitor_not_relabelled_resistor(self):
        script=fixture_script();script['steps'].append({'op':'figure','name':'circuit','labels':{'title':'RC capacitor charging'}})
        self.assertTrue(any('relabelled' in p for p in tutor.validate_script(script,subject='physics')))

    def test_22_capacity_is_error_not_silent_loss(self):
        steps=[]
        for i in range(tutor._SHEET_LIMIT+1):
            steps += [{'op':'caption','text':str(i)},{'op':'write','text':'Keep this content'}]
        with self.assertRaises(ValueError):tutor.normalize_script({'steps':steps})
    def test_23_old_cache_not_served_as_current(self):
        with patch.object(profile,'load_lesson',return_value=(fixture_script(),'old-signature')):
            self.assertEqual(self.client.get('/api/lesson/mathematics/numbers/data').status_code,409)
    def test_24_long_board_text_not_lost(self):
        text=' '.join(f'part{i}' for i in range(300))
        result=tutor.normalize_script({'steps':[{'op':'caption','text':'Long question'},{'op':'write','id':'question','text':text}]})
        reconstructed=' '.join(o['text'] for o in result['steps'] if o['op']=='write')
        self.assertEqual(reconstructed,text)
    def test_25_generation_saves_starting_signature(self):
        profile.set_current(self.a)
        with patch.object(web,'_lesson_sig',side_effect=['before','after']) as signature,patch.object(tutor,'generate_lesson',return_value=fixture_script()),patch.object(profile,'save_lesson') as save,patch.object(web,'_prefetch_narration'):
            web.generate_lesson('mathematics','numbers',self.a)
            self.assertEqual(signature.call_count,1)
            self.assertEqual(save.call_args.args[3],'before')

class StructuredLessonTests(unittest.TestCase):
    def content(self):
        sentence=("Explain the relationship carefully, identify the assumptions and keep each symbol consistent. "
                  "Substitution provides a separate check on the calculation, while a contrasting example shows why "
                  "the selected method applies only under the stated conditions. ")
        beat=lambda text: {'say':sentence*2,'write':text}
        return {'title':'Fixture',
                'core':[{'title':f'Concept {i}', 'beats':[beat('A key relationship'),beat('A contrasting condition')]} for i in range(8)],
                'examples':[{'title':f'Example {i}', 'question':'Calculate 2 + 3.',
                             'method':beat('Use addition'), 'steps':[beat('Start with 2'),beat('Add 1 to get 3'),beat('Add 1 to get 4'),beat('Add 1 to get 5')],
                             'answer':beat('2 + 3 = 5'), 'check':beat('5 - 3 = 2')} for i in range(4)]}
    def test_compiler_assigns_example_metadata_and_ids(self):
        script=tutor.normalize_script(tutor._structured_lesson_script(json.dumps(self.content()),'Fixture'),subject='mathematics')
        self.assertEqual(tutor.lesson_depth_problems(script),[])
        self.assertEqual(tutor.validate_script(script,subject='mathematics'),[])
        self.assertEqual(sum(o.get('section')=='example' for o in script['steps']),4)
        self.assertEqual(sum(o.get('section')=='continuation' for o in script['steps']),4)
        self.assertEqual(sum(o.get('id')=='answer' for o in script['steps']),4)
    def test_missing_working_rejected_before_playback(self):
        data=self.content();data['examples'][0]['steps']=[]
        with self.assertRaisesRegex(ValueError,'four to six'):tutor._structured_lesson_script(json.dumps(data),'Fixture')
    def test_empty_core_is_rejected(self):
        data=self.content();data['core'][0]['beats'][0]['write']=''
        with self.assertRaisesRegex(ValueError,'board line'):tutor._structured_lesson_script(json.dumps(data),'Fixture')
    def test_malformed_core_rejected_with_clear_error(self):
        data=self.content();data['core'][0]='heading only'
        with self.assertRaisesRegex(ValueError,'must be objects'):tutor._structured_lesson_script(json.dumps(data),'Fixture')
    def test_shallow_content_still_fails_depth(self):
        data=self.content()
        for section in data['core']:
            for beat in section['beats']:beat['say']='Too short.'
        for example in data['examples']:
            for beat in [example['method'],*example['steps'],example['answer'],example['check']]:beat['say']='Too short.'
        result=tutor.normalize_script(tutor._structured_lesson_script(json.dumps(data),'Fixture'))
        self.assertTrue(tutor.lesson_depth_problems(result))
    def test_generation_key_retires_previous_errors(self):
        self.assertTrue(web._gkey('physics','waves_ii',1).endswith(tutor.SCRIPT_VERSION))

    def test_changed_reference_question_rejected(self):
        data=self.content()
        with self.assertRaisesRegex(ValueError,'copy the supplied reference question exactly'):
            tutor._structured_lesson_script(json.dumps(data),'Fixture',[{'question':'Calculate 3 + 4.','reference_answer':'7'}])
    def test_reviewed_answer_is_authoritative(self):
        data=self.content();data['examples'][0]['answer']['write']='wrong model answer'
        result=tutor._structured_lesson_script(json.dumps(data),'Fixture',[{'question':'Calculate 2 + 3.','reference_answer':'5'}])
        self.assertIn({'op':'write','text':'5','id':'answer'},result['steps'])
        self.assertNotIn('wrong model answer',json.dumps(result))
    def test_scratch_dialogue_rejected(self):
        data=self.content();data['examples'][0]['check']['say']='I must have the formula wrong; wait while I guess again.'
        with self.assertRaisesRegex(ValueError,'checked solution'):
            tutor._structured_lesson_script(json.dumps(data),'Fixture')
    def test_physics_reviewed_examples_exist(self):
        for topic in ['waves_ii','capacitors']:
            anchors=tutor._lesson_reference_answers('physics',topic,[])
            self.assertEqual(len(anchors),4)
            self.assertTrue(all(r['reference_answer'] for r in anchors))

    def test_seven_sections_reflow_without_losing_teaching(self):
        data=self.content();data['core'].pop(2)
        result=tutor.normalize_script(tutor._structured_lesson_script(json.dumps(data),'Fixture'))
        self.assertEqual(tutor.lesson_depth_problems(result),[])
        self.assertEqual(sum(o.get('op')=='caption' for o in result['steps']),16)
        self.assertEqual(tutor.validate_script(result),[])

    def test_four_short_sections_assemble_one_full_lesson(self):
        data=self.content();part={'core':data['core'][:2],'example':data['examples'][0]}
        context=json.dumps({'topic':'Fixture','subject_slug':'mathematics'})
        with patch.object(tutor.llm,'chat',return_value=json.dumps(part)) as chat:
            result=tutor._generate_lesson_draft('',context,9999999999)
            self.assertEqual(chat.call_count,4)
            script=tutor.normalize_script(tutor._structured_lesson_script(result,'Fixture'))
            self.assertEqual(tutor.lesson_depth_problems(script),[])
            self.assertEqual(tutor.validate_script(script),[])
    def test_only_rejected_section_retries(self):
        data=self.content();part=json.dumps({'core':data['core'][:2],'example':data['examples'][0]})
        with patch.object(tutor.llm,'chat',side_effect=['{}',part,part,part,part]) as chat:
            result=tutor._generate_lesson_draft('',json.dumps({'topic':'Fixture','subject_slug':'mathematics'}),9999999999)
            self.assertEqual(chat.call_count,5)
            self.assertEqual(len(json.loads(result)['examples']),4)

    def test_reviewed_affected_topics_play_without_provider(self):
        for subject,topic in [('physics','waves_ii'),('mathematics','matrices_transformations')]:
            evidence=[{'question':'A saved fixture question','answer':'My earlier answer','feedback':'Use the correct units'}]
            with patch.object(tutor.llm,'chat',side_effect=AssertionError('provider should not be needed')):
                script=tutor.generate_lesson(subject,topic,[],'',evidence=evidence)
                self.assertEqual(tutor.validate_script(script,subject=subject),[])
                self.assertEqual(tutor.lesson_depth_problems(script),[])
                self.assertEqual(script['personalization'],evidence)
    def test_prose_beats_are_preserved(self):
        data=self.content();data['examples'][0]['method']='Use addition and verify by subtraction.'
        result=tutor._structured_lesson_script(json.dumps(data),'Fixture')
        self.assertIn('Use addition and verify by subtraction.',json.dumps(result))

    def test_openrouter_receives_requested_json_mode(self):
        response=Mock(status_code=200,text='ok')
        response.json.return_value={'choices':[{'message':{'content':'{"ok":true}'}}]}
        with patch.object(tutor.llm.requests,'post',return_value=response) as post:
            tutor.llm._openrouter_chat('system','user',0.1,500,json_mode=True)
            self.assertEqual(post.call_args.kwargs['json']['response_format'],{'type':'json_object'})
            tutor.llm._openrouter_chat('system','user',0.1,500,json_mode=False)
            self.assertNotIn('response_format',post.call_args.kwargs['json'])

    def test_primary_timeout_preserves_fallback_budget(self):
        with patch.object(tutor.llm,'_or_ready',return_value=True),patch.object(tutor.llm.requests,'post',side_effect=tutor.llm.requests.ReadTimeout('fixture timeout')) as post:
            with self.assertRaises(tutor.llm.ProviderUnavailable):
                tutor.llm._gemini_chat('system','user',0.1,500,True)
            self.assertEqual(post.call_count,1)
            self.assertLessEqual(post.call_args.kwargs['timeout'],30)

    def test_native_schema_is_forwarded(self):
        response=Mock(status_code=200,text='ok')
        response.json.return_value={'choices':[{'message':{'content':'{"ok":true}'}}]}
        schema=tutor._lesson_segment_schema('physics')
        anchored=tutor._lesson_segment_schema('physics',{'question':'Find Q for 20 µF at 12 V.'})
        self.assertEqual(anchored['properties']['example']['properties']['question']['enum'],['Find Q for 20 µF at 12 V.'])
        with patch.object(tutor.llm.requests,'post',return_value=response) as post:
            tutor.llm._openrouter_chat('system','user',0.1,500,json_mode=True,response_schema=schema)
            format=post.call_args.kwargs['json']['response_format']
            self.assertEqual(format['type'],'json_schema')
            self.assertTrue(format['json_schema']['strict'])
            self.assertEqual(format['json_schema']['schema']['properties']['core']['maxItems'],2)
        response.json.return_value={'candidates':[{'content':{'parts':[{'text':'{"ok":true}'}]}}]}
        with patch.object(tutor.llm.requests,'post',return_value=response) as post:
            tutor.llm._gemini_chat('system','user',0.1,500,True,response_schema=schema)
            self.assertEqual(post.call_args.kwargs['json']['generationConfig']['responseJsonSchema'],schema)

if __name__=='__main__':unittest.main()
