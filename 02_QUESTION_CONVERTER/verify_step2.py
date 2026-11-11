#!/usr/bin/env python3
"""Verify converter contract and source fidelity; never opens answers.jsonl."""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sqlite3
import sys

EXPECTED_IDS={
"q_0c8f3e07768f","q_0cb7c9b93048","q_1cc70c12aa27","q_20aa992c0d3f",
"q_38e2b6cef714","q_62a9a454f35b","q_7c8afb8a81e9","q_fcbf1e1cd8d4",
"q_c893acce3ef3","q_15fd3e0d0363"}

def jsonl(p):
    return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]

def verify(step1,out):
    converted=jsonl(out/'converted_questions.jsonl')
    originals={x['id']:x for x in jsonl(step1/'benchmark/questions_biz_101.jsonl')}
    rules={x['id'] for x in json.loads((step1/'business_rules.json').read_text(encoding='utf-8'))['rules']}
    schema=json.loads((out/'converted_question.schema.json').read_text(encoding='utf-8'))
    known_cols={c['name'] for t in json.loads((step1/'schema.json').read_text(encoding='utf-8'))['tables'] if t['name']=='sales_lines' for c in t['columns']}
    assert len(converted)==10 and {x['question_id'] for x in converted}==EXPECTED_IDS
    assert len({x['question_id'] for x in converted})==10
    db=sqlite3.connect('file:'+str((step1/'biz_101.sqlite').resolve())+'?mode=ro',uri=True)
    db.execute('PRAGMA query_only=ON')
    observed_names={x[0] for x in db.execute('select distinct product_name from sales_lines')}
    statuses={x[0] for x in db.execute('select distinct order_status from sales_lines')}
    assert {'Xong','Đang giao','Đã hủy','Đổi trả'} == statuses
    try:
        import jsonschema
    except ImportError:
        print('NOTE: jsonschema unavailable; using structural/source validation only')
    else:
        for c in converted: jsonschema.validate(c,schema)
    counts={'source_fidelity':0,'time':0,'schema':0,'business_rules':0,'real_entities':0,'no_answer_leakage':0}
    for r in converted:
        orig=originals[r['question_id']]
        assert (r['business_id'],r['original_question'],r['as_of_date'])==(orig['business_id'],orig['question'],orig['as_of_date'])
        counts['source_fidelity']+=1
        t=r['temporal_constraints'];start=dt.date.fromisoformat(t['start_date']);end=dt.date.fromisoformat(t['end_date']);asof=dt.date.fromisoformat(r['as_of_date'])
        assert start<=end<=asof and t['reference_date']==r['as_of_date']
        if t['normalization_kind']=='relative_previous_day': assert start==end==asof-dt.timedelta(days=1)
        if t['normalization_kind']=='relative_today': assert start==end==asof
        assert t['inclusive_start'] and t['inclusive_end']
        counts['time']+=1
        intent=r['intent'];assert intent['measure_column'] in known_cols
        assert all(x in known_cols for x in intent['group_by'])
        assert all(f['field'] in known_cols for f in intent['filters'])
        assert intent['required_relations']==['sales_lines'] and intent['needs_join'] is False
        if intent['metric']=='valid_order_count': assert intent['aggregation']=='count_distinct' and intent['measure_column']=='order_id'
        if intent['metric']=='net_sales_revenue':assert intent['measure_column']=='line_amount_vnd'
        if intent['metric']=='sold_base_quantity':assert intent['measure_column']=='base_quantity'
        if intent['metric']=='unit_selling_price':
            assert intent['measure_column']=='sale_price_vnd'
            assert 'order_status' not in {f['field'] for f in intent['filters']}, 'price lookup must include canceled/returned orders'
        else:
            assert any(f['field']=='order_status' and set(f['value'])=={'Xong','Đang giao'} for f in intent['filters'])
        counts['schema']+=1
        assert set(x['id'] for x in r['required_business_rules']) <= rules
        counts['business_rules']+=1
        if intent['entity']:
            assert intent['entity']['observed_aliases']
            assert set(intent['entity']['observed_aliases'])<=observed_names
        counts['real_entities']+=1
        for key in ('answer','gold_answer','ground_truth','reference_sql','solution_sql'):
            assert key not in r
        assert r['status']=='ready' and r['ambiguities']==[]
        counts['no_answer_leakage']+=1
    by_id={r['question_id']:r for r in converted}
    assert (by_id['q_0c8f3e07768f']['temporal_constraints']['start_date'],by_id['q_0c8f3e07768f']['temporal_constraints']['end_date'])==('2025-10-01','2025-12-31')
    assert by_id['q_0cb7c9b93048']['temporal_constraints']['start_date']=='2025-09-23'
    assert by_id['q_1cc70c12aa27']['temporal_constraints']['start_date']=='2026-02-22'
    assert by_id['q_20aa992c0d3f']['intent']['group_by']==['order_date'] and by_id['q_20aa992c0d3f']['intent']['top_k']==1
    assert by_id['q_38e2b6cef714']['intent']['group_by']==['product_name'] and by_id['q_38e2b6cef714']['intent']['measure_column']=='base_quantity'
    assert len(by_id['q_62a9a454f35b']['intent']['entity']['observed_aliases'])==2, 'Coca two spellings should both be covered'
    assert by_id['q_7c8afb8a81e9']['intent']['requested_unit']=='kg'
    assert by_id['q_fcbf1e1cd8d4']['intent']['price_semantics']['include_canceled_and_returned_orders'] is True
    assert by_id['q_15fd3e0d0363']['temporal_constraints']['end_date']=='2026-02-28'
    assert by_id['q_c893acce3ef3']['intent']['entity'] is None
    counts['focused_semantic_invariants']=10
    db.close()
    return counts

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--step1',type=pathlib.Path,default=pathlib.Path('../datamate_step1_biz101'))
    p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('.'))
    a=p.parse_args()
    result=verify(a.step1.resolve(),a.out.resolve())
    print('STEP 2 VERIFIED',json.dumps(result,ensure_ascii=False))
