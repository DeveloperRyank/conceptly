# Teaching content and lesson playback

Build the generated notes and banks with `python tools/build_teaching_content.py`.
Edit `tools/content/*.json`, not `data/*/notes/*.md` or the generated CSVs.
Use `--check` to verify byte-for-byte reproducibility.

Current coverage follows the existing KCSE topic taxonomy (not a new syllabus):

| Subject | Topic groups with notes and practice | Questions | Reference answers |
| --- | ---: | ---: | ---: |
| Chemistry | 31 | 284 | 109 |
| Computer Studies | 10 | 45 | 45 |
| Mathematics | 16 | 64 | 64 |
| Physics | 42 practice topics | 50 | 50 |

Chemistry preserves the 175 legacy records and their field values in their original
order. New material is 93 original practice items and 16 reviewed booklet-derived
pairs. Computer Studies contains 30 original items and 15 reviewed booklet-derived
pairs. Mathematics contains 64 original worked practice items. Original material is
not claimed to be past-paper content. Source document hashes and locations are in
`tools/content/`; those metadata do not enter student-facing notes or exam HTML.

The booklet import is deliberately selective, not exhaustive. Withheld material
includes missing diagrams/tables, ambiguous or unmatched question-answer blocks,
incorrect or unreliable answers, duplicate items and practical papers. In particular,
the Computer Studies source has errors involving spam, search-engine examples,
relative references and some arithmetic; these blocks were not imported. No claim
is made that the booklets or official syllabuses have been exhaustively covered.

## Checks

- `python tools/test_teaching.py`: 48 integration checks, with temporary profile DBs.
- `node tools/test_voice.js`: controlled audio clock, pending synthesis pause,
  actual clip duration, playback rate, pause/resume and completion.
- `python tools/test_lesson_browser.py`: Chromium at 1280 and 390 px; isolated
  accounts, real auth/CSRF, fixture lessons, mocked recognition/AI. Automatic
  listening, keyword question capture, resume/restart/permission denial, inline
  Maths diagrams, hardware diagram, calculator, mouse/touch drawings, draft
  reload, image submission and results, and unchanged theory widgets.
- `node tools/test_exam_tools.js`: calculator precedence, degree functions,
  invalid expressions and drawing-question eligibility.
- `python tools/build_physics_questions.py --check`: 50 reviewed original or
  lesson-example questions, with server-only reference answers, across 42 topics.
- `python tools/build_teaching_content.py --check`: reproducible generated assets.
- `git diff --check` and JavaScript/Python syntax checks.

The primary provider and hosted TTS are unchanged. Local credentials were not
available, so real-provider verification ran in isolated Vercel previews with
production-equivalent settings and synthetic learner evidence, calling the tutor
directly without importing the profile database. Fixture tests do not establish
semantic correctness: failed live drafts were read and withheld, and the final
capacitor draft was reviewed end to end. Audible speech, real microphones and
real-device performance still require device checks. Recognition now starts
automatically where supported, subject to browser microphone permission. A denied
permission stops retries; typing and the ask button remain available.

The lesson player retains its colours, uses flat controls, and defaults to 1.25×.
The profile disclosure and separate Explore section are removed. Projected 3D
cuboid/vector diagrams are timed Maths lesson sheets. Other subjects use 2D
apparatus, system diagrams or reviewed topic maps. Figure generation is restricted
by subject/topic, and generic graphs are excluded from Computer Studies.

Exam drawings use local pointer strokes plus PNG submission to the existing Gemini
vision route. Unreadable images fail without invented grades. Reference answers
remain server-side. Drawn drafts are retained on this device for correction after
marking errors; use Start fresh to discard them. Vision-provider quality is not
established by mocked tests. Viewing diagrams never records mastery.

VoiceStudio support is an optional server-side `/v1/audio/speech` connector, tested
against its documented API contract. It is NOT activated: a persistent HTTPS
VoiceStudio host, its configured voice/model and private API credential are still
needed. No VoiceStudio model can run inside this Vercel function. Current narration
continues until that service is configured. See `tools/VOICE_STUDIO.md`.


## Lesson failure repair

Runtime logs identified rejected drafts on `matrices_transformations` and
`waves_ii`: 168/286 spoken words, missing example section markers, and empty board
sheets. A first structured single-call attempt also proved unreliable in live
preview tests: invalid schema counts, incorrect checks, and a provider timeout.
Those drafts were withheld, not served to students.

Matrices and Waves II now use reviewed complete base lessons (1,414 and 1,561
spoken words respectively, 16 sheets and four worked examples each). Saved learner
mistakes are prepended through the same account-scoped evidence path, and AI
follow-up questions remain available. These lessons do not require a new provider
completion before playback. Their content participates in cache fingerprints.

Other topics use four shorter parallel provider requests with independent section
retries, a typed content compiler, authoritative bank reference answers, and the
unchanged final playback/depth validators. The primary Gemini provider and hosted TTS configuration remain unchanged. The
existing OpenRouter fallback uses a free model advertising JSON-output support
(`nvidia/nemotron-3.5-super-vl:free`); JSON mode is now forwarded to OpenRouter.
A stalled text request to Gemini yields to that existing fallback after 30 seconds,
preserving the lesson budget. Vision requests retain their original timeout. New generation-job keys retire the old persisted failures. Invalid
content receives a specific draft-quality message rather than the generic support
error. Regression coverage includes missing content, schema variation, preserved
prose beats, section assembly and retries, reviewed playback without a provider,
real saved-evidence recall, and cache revision behaviour.

Final live checks: reviewed Matrices and Waves II each prepared a valid lesson in
about 0.01 seconds; the native-schema AI path produced 1,270 words, four examples
and 17 sheets including synthetic recall in 10.9 seconds. Reviewed capacitor
foundations and corrected discharge wording produced a final compiled 1,356-word
lesson. Those actual lesson scripts passed Chrome playback checks at 1280 and
390 px. Native schema enforces the exact reference question and response shape;
local validators continue to enforce depth, complete questions and playability.
