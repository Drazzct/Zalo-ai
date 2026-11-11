#!/usr/bin/env python3
"""Validate only STEP 1 & 2 artifacts, data provenance, answer isolation and the handoff."""
from pathlib import Path
from zipfile import ZipFile
import hashlib,json,sqlite3,sys

ROOT=Path(__file__).resolve().parent
H=ROOT/'HANDOFF_AFTER_STEP2'
RAW=ROOT/'00_RAW_INPUT'
S1=ROOT/'01_PREPROCESSING'
S2=ROOT/'02_QUESTION_CONVERTER'
MAP={
    '01_PREPROCESSING/schema.json':'schema.json',
    '01_PREPROCESSING/business_rules.json':'business_rules.json',
    '01_PREPROCESSING/data_dictionary.md':'data_dictionary.md',
    '01_PREPROCESSING/biz_101.sqlite':'database/biz_101.sqlite',
    '02_QUESTION_CONVERTER/converted_questions.jsonl':'converted_questions.jsonl',
    '02_QUESTION_CONVERTER/converted_question.schema.json':'converted_question.schema.json'
}
SRC=['train/data/biz_101/README.md','train/data/biz_101/ban_hang.csv','train/rulebook.md','train/calendar.csv','train/questions.jsonl']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def jsonl(p):return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def main():
    errors=[]
    actual_files=[p for p in ROOT.rglob('*') if p.is_file()]
    forbidden=['coder_inputs.jsonl','prompt_builder.py','qwen25_coder_requests.jsonl','qwen3_nonthinking_requests.jsonl','qwen3_thinking_requests.jsonl','answers.jsonl','answers_biz_101.jsonl','model_response.schema.json','build_step3.py']
    for path in actual_files:
        if path.name.lower() in forbidden:errors.append('FORBIDDEN FILE: '+str(path.relative_to(ROOT)))
    with ZipFile(RAW/'train_biz101_no_labels.zip') as z:
        assert z.testzip() is None
        assert set(n for n in z.namelist() if not n.endswith('/'))==set(SRC), 'mini archive unexpected/missing members'
        for member in SRC:
            assert hashlib.sha256(z.read(member)).hexdigest()==sha(RAW/member), 'Raw file hash mismatch: '+member
    for src,dst in MAP.items():
        assert sha(ROOT/src)==sha(H/dst), 'Handoff differs from upstream: '+dst
    qs=jsonl(S1/'benchmark/questions_biz_101.jsonl')
    cq=jsonl(S2/'converted_questions.jsonl')
    rawq=jsonl(RAW/'train/questions.jsonl')
    assert len(qs)==40 and len(cq)==10 and len(rawq)==3000,(len(qs),len(cq),len(rawq))
    assert len({q['question_id'] for q in cq})==10
    byid={q['id']:q for q in qs}
    rules=json.loads((S1/'business_rules.json').read_text(encoding='utf-8'))
    valid_rule_ids={r['id'] for r in (rules if isinstance(rules,list) else rules.get('rules',[]))}
    for r in cq:
        assert r['business_id']=='biz_101' and r['question_id'] in byid
        assert r['original_question']==byid[r['question_id']]['question']
        assert r['as_of_date']==byid[r['question_id']]['as_of_date']
        assert r['status']=='ready'
        assert all(v['id'] in valid_rule_ids for v in r['required_business_rules'])
        assert not any(k in r for k in ('answer','ground_truth','reference_sql','solution_sql'))
    db=sqlite3.connect('file:'+str((H/'database/biz_101.sqlite').resolve())+'?mode=ro',uri=True)
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    lines=db.execute('SELECT COUNT(*) FROM sales_lines').fetchone()[0]
    orders=db.execute('SELECT COUNT(DISTINCT order_id) FROM sales_lines').fetchone()[0]
    assert (lines,orders)==(56501,22428),(lines,orders)
    db.close()
    assert not errors,'\n'.join(errors)
    print('PASS: 5 raw sources identical to mini archive; 40 real biz_101 questions; 10 converted questions')
    print('PASS: 6 handoff files identical to STEP 1/2; rules/IDs/anchors consistent')
    print(f'PASS: SQLite {lines} item rows, {orders} orders, integrity OK; no ground truth or Step 3 outputs')

if __name__=='__main__':main()
