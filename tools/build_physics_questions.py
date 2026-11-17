"""Build original, reviewed Physics practice; never label these as actual past papers."""
import csv
import io
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import curriculum
rows=json.loads((ROOT/'tools/content/physics_questions.json').read_text())
assert all(r['topic'] in curriculum.all_topic_slugs('physics') and r['question'] and r['reference_answer'] for r in rows)
assert len({r['question'] for r in rows})==len(rows)
buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=['question','topic','reference_answer'],extrasaction='ignore',lineterminator='\n');writer.writeheader();writer.writerows(rows)
path=ROOT/'data/physics/questions.csv'
if '--check' in sys.argv:
    assert path.read_text()==buf.getvalue(), 'Rebuild Physics questions'
else:path.write_text(buf.getvalue())
print(f'{len(rows)} reviewed Physics questions across {len({r["topic"] for r in rows})} topics.')
