import json
from pathlib import Path

def analyze_all_logs():
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

    with open('result/all_logs.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict):
        items = list(data.values())
    else:
        items = data

    print(f"Total questions in all_logs.json: {len(items)}")
    print("=" * 80)

    matched = 0
    total = len(items)

    for i, item in enumerate(items):
        qid = item.get('id')
        q_info = q_map.get(qid, {})
        gt_info = gt_map.get(qid, {})
        pred = item.get('final_answer', {})
        traces = item.get('trace', [])
        elapsed = item.get('elapsed_seconds', 0)

        gt_type = gt_info.get('type')
        gt_ans = gt_info.get('answer', gt_info.get('reason'))
        pred_type = pred.get('type')
        pred_ans = pred.get('answer', pred.get('reason'))

        is_match = False
        if pred_type == gt_type:
            if str(pred_ans).strip() == str(gt_ans).strip():
                is_match = True
            elif isinstance(pred_ans, (int, float)) and isinstance(gt_ans, (int, float)):
                if abs(float(pred_ans) - float(gt_ans)) <= 0.05:
                    is_match = True

        if is_match:
            matched += 1
            status = "✅ MATCH"
        else:
            status = "❌ MISMATCH"

        print(f"[{i+1}/{total}] {status} | QID: {qid} | Shop: {q_info.get('business_id')} | As of: {q_info.get('as_of_date')}")
        print(f"  Câu hỏi: {q_info.get('question')}")
        print(f"  Dự đoán: {pred_type} -> {pred_ans}")
        print(f"  Ground Truth: {gt_type} -> {gt_ans}")
        print(f"  Thời gian: {elapsed}s | Số lần thử (Attempts): {len(traces)}")

        if not is_match:
            print("  --- CHI TIẾT CÁC LẦN THỬ (TRACES) ---")
            for tr in traces:
                att = tr.get('attempt')
                err = tr.get('exec_error') or tr.get('execution_error')
                succ = tr.get('exec_success')
                code = tr.get('code') or tr.get('generated_code')
                raw = tr.get('raw_response') or ''
                print(f"    * Lần thử {att}: Success={succ} | Lỗi: {err}")
                if code:
                    first_line = code.strip().split('\n')[0]
                    last_line = code.strip().split('\n')[-1]
                    print(f"      Code len: {len(code)} ký tự | Dòng đầu: {first_line} | Dòng cuối: {last_line}")
                else:
                    print(f"      Không có code sinh ra! Độ dài phản hồi: {len(raw)} ký tự")
                    if raw:
                        print(f"      Đoạn cuối raw_response:\n{raw[-250:]}")
        print("-" * 80)

    print(f"\nTỔNG KẾT: {matched}/{total} câu chính xác ({(matched/total)*100:.1f}%)")

if __name__ == '__main__':
    analyze_all_logs()
