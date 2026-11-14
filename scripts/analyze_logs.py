import json
import glob
from pathlib import Path

def analyze():
    gt_map = {}
    with open('train/answers.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                it = json.loads(line)
                gt_map[it['id']] = it

    q_map = {}
    with open('train/questions.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                it = json.loads(line)
                q_map[it['id']] = it

    log_files = sorted(glob.glob('result/logs/*.json'))
    print(f"Total log files found: {len(log_files)}")
    print("=" * 80)

    matches = 0
    total = len(log_files)

    for lf in log_files:
        with open(lf, 'r', encoding='utf-8') as f:
            data = json.load(f)
        qid = data['id']
        q_item = q_map.get(qid, {})
        gt_item = gt_map.get(qid, {})
        pred = data['final_answer']
        traces = data.get('trace', [])
        last_tr = traces[-1] if traces else {}

        gt_type = gt_item.get('type')
        gt_ans = gt_item.get('answer', gt_item.get('reason'))
        pred_type = pred.get('type')
        pred_ans = pred.get('answer', pred.get('reason'))

        match = False
        if pred_type == gt_type:
            if str(pred_ans).strip() == str(gt_ans).strip():
                match = True
            elif isinstance(pred_ans, (int, float)) and isinstance(gt_ans, (int, float)):
                if abs(float(pred_ans) - float(gt_ans)) <= 0.05:
                    match = True

        if match:
            matches += 1

        status = "MATCH" if match else "MISMATCH"
        print(f"[{status}] QID: {qid} | Shop: {q_item.get('business_id')} | As of: {q_item.get('as_of_date')}")
        print(f"  Question: {q_item.get('question')}")
        print(f"  Pred: {pred_type} -> {pred_ans}")
        print(f"  GT:   {gt_type} -> {gt_ans}")
        print(f"  Elapsed: {data.get('elapsed_seconds'):.1f}s | Attempts: {len(traces)} | Exec: {last_tr.get('exec_success')}")
        if not last_tr.get('exec_success'):
            err = str(last_tr.get('exec_error', ''))
            print(f"  Error: {err[:200]}")
        print("-" * 80)

    print(f"SUMMARY: {matches}/{total} matched ({matches/total*100:.1f}%)" if total else "No logs found.")

if __name__ == '__main__':
    analyze()
