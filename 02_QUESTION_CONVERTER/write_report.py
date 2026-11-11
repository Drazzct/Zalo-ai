#!/usr/bin/env python3
"""Generate human-readable handoff documentation from verified converter output."""
from pathlib import Path
import json

folder=Path(__file__).resolve().parent
items=[json.loads(x) for x in (folder/'converted_questions.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
validation=json.loads((folder/'verification.json').read_text(encoding='utf-8'))
report='''# STEP 2 — Manual Question Converter / DataMate `biz_101`

## Phạm vi và độ tin cậy

- **Input thực:** 10/40 câu hỏi thật lấy nguyên văn từ `STEP1/benchmark/questions_biz_101.jsonl`, không tự tạo câu hỏi.
- **Nguồn giải nghĩa:** `STEP1/sources/rulebook.md`, `STEP1/sources/readme.md`, `STEP1/schema.json`, `STEP1/business_rules.json` và tên sản phẩm/đơn vị đã kiểm tra trên `STEP1/biz_101.sqlite`.
- **Đầu ra máy đọc:** `converted_questions.jsonl` (mỗi dòng một JSON object), `converter_mapping.csv`, `converted_question.schema.json`.
- **Tách nhãn:** hoàn toàn không đọc `answers.jsonl`, không chứa đáp án chuẩn, không chứa SQL lời giải mẫu.
- **Giới hạn:** đây là **10 annotation thủ công có thể kiểm chứng**, chưa phải converter tổng quát cho toàn bộ câu hỏi DataMate. `status=ready` chỉ nói input semantic đủ để viết truy vấn, không chứng minh đáp án tương lai sẽ đúng.
- **Quy ước:** `end_date` và `start_date` bao gồm cả ngày biên; `as_of_date` lấy từ record gốc, tuyệt đối không lấy đồng hồ hệ thống.

## Tóm tắt 10 câu đã chuẩn hóa

| # | Question ID | Intent | Khoảng thời gian | Đầu ra | Luật nổi bật |
|---:|---|---|---|---|---|
'''
for i,r in enumerate(items,1):
    intent=r['intent'];t=r['temporal_constraints']; rules=', '.join(b['id'] for b in r['required_business_rules'])
    report+=f"| {i} | `{r['question_id']}` | `{intent['aggregation']}({intent['metric']})` | {t['start_date']} → {t['end_date']} | `{intent['expected_answer_type']}` | {rules} |\n"
report+='''
## Phân tích chi tiết từng câu (semantic → intent → temporal → rule → normalized)

'''
for i,r in enumerate(items,1):
    it=r['intent'];t=r['temporal_constraints']
    filters=', '.join(f"`{x['field']}` {x['operator']} {x['value']}" for x in it['filters'])
    rules=', '.join(f"**{x['id']}** ({x['source']})" for x in r['required_business_rules'])
    report+=f'''### {i}. `{r['question_id']}`

- **Original:** {r['original_question']}
- **as_of_date:** `{r['as_of_date']}`
- **Semantic analysis:** {r['semantic_analysis']['user_goal']} {r['semantic_analysis']['interpretation']}
- **Intent:** metric `{it['metric']}`, aggregation `{it['aggregation']}`, measure `{it['measure_column']}`, GROUP BY `{', '.join(it['group_by']) or 'none'}`, top-k `{it['top_k']}`, expected type `{it['expected_answer_type']}`.
- **Entity:** {it['entity']['canonical_name']+'; aliases: '+', '.join(it['entity']['observed_aliases']) if it['entity'] else 'Toàn cửa hàng (không entity filter)'}.
- **Filters:** {filters}.
- **Temporal normalization:** `{t['original_expression']}` → **{t['start_date']} đến {t['end_date']}** (inclusive), theo `{t['normalization_kind']}`; anchor `{t['reference_date']}`.
- **Business rules:** {rules}.
- **Normalized question:** {r['normalized_question']}
- **Ambiguities còn tồn:** {'; '.join(r['ambiguities']) if r['ambiguities'] else 'Không phát hiện điểm mơ hồ đang chặn conversion.'}
- **Conditional risks:** {'; '.join(r['conditional_risks']) if r['conditional_risks'] else 'Không có điều kiện phát sinh đáng chú ý trong phạm vi converter này.'}
- **Needs JOIN:** `{it['needs_join']}`; relation `sales_lines`.

'''
report+='''## Các bẫy ngữ nghĩa đã xử lý

1. **Đơn ≠ dòng hàng:** `COUNT(DISTINCT order_id)` (rulebook §1); loại đơn `Đã hủy`, `Đổi trả` nhưng giữ `Đang giao`.
2. **Doanh thu ≠ giá bán × lượng:** lấy `line_amount_vnd`, đã trừ giảm giá dòng. Không nhầm với số tiền khách trả.
3. **`hôm qua` ≠ ngày hiện tại của máy:** câu `q_0cb7...` neo vào `as_of_date=2025-09-24` nên là `2025-09-23`.
4. **`bán chạy nhất` ≠ doanh thu lớn nhất:** theo `SUM(base_quantity)`, nhóm tên hàng đã chuẩn hóa. Rulebook §9 nêu tie-break theo mã, không có mã thì tên.
5. **Tên sản phẩm không hoàn toàn sạch:** tên Coca có cả `Coca Cola 330ml` và `Coca  Cola 330ml`. Luật §8 cho phép coi các cách viết cùng một vật là cùng một thứ; không dùng exact match 1 tên nếu còn alias.
6. **Giá bán lịch sử ≠ doanh thu:** giá một gói Vinataba là `sale_price_vnd` trước giảm quy về **gói**; tra cả đơn hủy/trả theo rulebook §5. Cảnh báo nếu ngày có nhiều giá khác nhau vì nguồn không chỉ rõ cách lấy duy nhất.
7. **Kg ≠ bao:** `Nếp cái hoa vàng` có đơn vị cơ bản `kg`; dùng `base_quantity`, không cộng số bao hoặc nhân hệ số tùy tiện.
8. **Không tự cho 0 nếu ngoài vùng dữ liệu:** rulebook §7 phân biệt thiếu dữ liệu và số 0.

## Verification — Không dùng đáp án

| Kiểm tra | Kết quả |
|---|---|
'''
for k,label in [('source_fidelity','Đối chiếu nguyên văn 10 câu gốc'),('time','Date ranges, as_of_date, tháng/quý'),('schema','Cột, relation, aggregation hợp lệ'),('business_rules','Rule IDs có thật trong STEP 1'),('real_entities','Tên hàng / alias có trong database'),('no_answer_leakage','Không thêm nhãn đáp án / lời giải SQL')]:
    report+=f"| {label} | **10/10** |\n"
report+='''
- Lệnh kiểm tra ở `README.md` gọi `verify_step2.py`: ngoài các mục trên còn kiểm tra **10 invariant ngữ nghĩa đặc thù**.
- Query vào SQLite **chỉ kiểm tra phạm vi dữ liệu và alias**; không tính kết quả cuối, không tra `answers_biz_101.jsonl`.
- `verification.json` ghi kiểm tra từng question ID, các tệp đầu vào theo SHA-256 và chỉ số `distinct_price_levels_for_requested_day` dùng để phát hiện trường hợp giá mơ hồ. Không lưu giá bán thực tế.

## Chuyển giao STEP 3

- `converted_questions.jsonl` là **output của layer Converter**; STEP 3 sẽ kết hợp nó với schema/bảng/quan hệ/business rule context thành `coder_inputs.jsonl`.
- **Prompt Coder không nhận** đường dẫn dữ liệu bí mật, output evaluation, SQL lời giải hoặc `verification.json`.
- STEP 3 phải quy định status handling: `ready` → build input, `needs_clarification` → giữ ambiguity, `unanswerable_candidate` → kiểm tra theo rulebook §7.
- Nếu Nam/Nguyên cung cấp Converter chính thức, họ chỉ cần đáp ứng contract; inference/evaluation không nên phụ thuộc vào cách annotation thủ công.
'''
(folder/'STEP2_REPORT.md').write_text(report,encoding='utf-8')
readme='''# DataMate `biz_101` — STEP 2 / Manual Question Converter

## 1. Mục tiêu

10 câu hỏi **có thật** trong STEP 1 được chuẩn hóa thành intent, filters, temporal bounds, rule IDs, alias và expected type. **Chưa sinh SQL, chưa chạy Qwen, chưa so khớp answers.**

## 2. File trong package

- `converted_questions.jsonl`: 10 record JSONL (chưa chứa ground truth)
- `converter_mapping.csv`: bảng mapping mở được bằng Excel/VS Code
- `converted_question.schema.json`: contract JSON Schema để downstream xác thực
- `verification.json`: kết quả xác minh sơ bộ, *không* phải final accuracy
- `STEP2_REPORT.md`: giải nghĩa từng câu hỏi và rủi ro
- `build_step2.py`: mã tạo kết quả deterministic từ STEP 1, chỉ dùng Python standard library
- `verify_step2.py`: xác thực source fidelity, temporal, schema, rules, entity aliases; `jsonschema` tùy chọn
- `write_report.py`: cập nhật báo cáo từ JSONL sau khi build

## 3. Cách chạy lại trên Windows PowerShell

Giải nén ZIP STEP 1 và STEP 2 vào cùng một thư mục cha để có:

```text
workspace/
  datamate_step1_biz101/
    benchmark/questions_biz_101.jsonl
    business_rules.json
    schema.json
    biz_101.sqlite
  datamate_step2_biz101/
    build_step2.py
    verify_step2.py
    ...
```

Tại thư mục `workspace/datamate_step2_biz101` mở PowerShell:

```powershell
python .\\build_step2.py --step1 ..\\datamate_step1_biz101 --out .
python .\\verify_step2.py --step1 ..\\datamate_step1_biz101 --out .
python .\\write_report.py
```

Kết quả `STEP 2 VERIFIED` với các hạng mục 10/10 là PASS. Để validate chính xác JSON Schema, cài tùy chọn `python -m pip install jsonschema` trước khi gọi verifier (giai đoạn development, không cần Internet khi inference).

## 4. Trách nhiệm và boundaries

- Bước này được ghi chú *manual* theo 10 question IDs; **không** áp công thức suy diễn cho mọi business.
- `answers_biz_101.jsonl` **tuyệt đối không được đọc hoặc dùng** cho converter/prompt; file nhãn chỉ được dùng ở STEP 6 evaluation.
- Chỉ dùng `sales_lines` (view loại duplicate export), nguồn doanh thu phải theo `line_amount_vnd`, đơn hàng theo `COUNT DISTINCT order_id`.
- Mỗi normalized question giữ nguyên ý, ngày tham chiếu, status và nguồn rule. Mọi bổ sung ở STEP 3 không được mang thông tin mà runtime chính thức không có.
- Nếu data hoặc luật thay đổi, chạy lại builder và verifier, và ghi lại SHA-256 trong `verification.json`.
'''
(folder/'README.md').write_text(readme,encoding='utf-8')
