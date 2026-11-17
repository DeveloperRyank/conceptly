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

- `python tools/test_teaching.py`: 25 integration checks, with temporary profile DBs.
- `node tools/test_voice.js`: controlled audio clock, pending synthesis pause,
  actual clip duration, playback rate, pause/resume and completion.
- `python tools/test_lesson_browser.py`: Chromium at 1280 and 390 px; real session
  auth/CSRF with fixture lessons and mocked speech recognition/answers. Profile
  display, keyword interruption, ask/resume, narration preservation, 3D model
  controls, reduced motion, apparatus models, no page errors or profile writes.
- `python tools/build_teaching_content.py --check`: reproducible generated assets.
- `git diff --check` and JavaScript/Python syntax checks.

The LLM provider is unchanged. A fresh live generation and semantic review require
the existing provider key/model in the local environment. This environment did not
have them configured, so fixture tests do not demonstrate real model teaching
quality. The prompt explicitly addresses charge-averaged capacitor voltage,
rounding, physical derivations, defined discharge paths and independent checks.
The validator rejects shallow structural output; word counts do not establish
semantic correctness. Audible speech, real microphones and real-device performance
still require device checks. Browser recognition support varies and is opt-in;
typed questions and the existing ask button remain available.

3D is an optional local projected model on selected relevant topics (cuboids,
vectors, methane and water). Other supported diagrams offer schematic apparatus
or data-flow exploration. Lessons retain the written board; this is not a conversion
of every lesson into a 3D scene. Exploration and viewing never record mastery.
