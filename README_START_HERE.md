# DataMate biz_101 — Raw Input → Preprocessing → Question Converter

**PHẠM VI CHÍNH XÁC:** Gói dữ liệu mẫu cho pipeline của Nam (Preprocessing) + Nguyên (Question Converter). Chỉ dừng tại STEP 2. Không xây hoặc bàn giao Coder Input Builder / prompt Qwen / Qwen predictions.

## Cấu trúc

```text
DataMate_biz101_RAW_to_STEP2_ONLY/
├── 00_RAW_INPUT/
│   ├── train/
│   │   ├── calendar.csv
│   │   ├── rulebook.md
│   │   ├── questions.jsonl
│   │   └── data/biz_101/
│   │       ├── README.md
│   │       └── ban_hang.csv
│   └── train_biz101_no_labels.zip
├── 01_PREPROCESSING/
│   ├── analyze_step1.py, finalize_step1.py
│   ├── biz_101.sqlite
│   ├── schema.json, schema.sql
│   ├── business_rules.json, data_dictionary.md
│   ├── data_profile.json, inventory.json, verification.json
│   ├── sources/ (5 file gốc)
│   └── benchmark/questions_biz_101.jsonl (40 câu)
├── 02_QUESTION_CONVERTER/
│   ├── build_step2.py, verify_step2.py, write_report.py
│   ├── converted_questions.jsonl (10 câu)
│   ├── converted_question.schema.json
│   ├── converter_mapping.csv, verification.json
│   └── STEP2_REPORT.md
├── HANDOFF_AFTER_STEP2/
│   ├── converted_questions.jsonl
│   ├── converted_question.schema.json
│   ├── schema.json
│   ├── business_rules.json
│   ├── data_dictionary.md
│   └── database/biz_101.sqlite
├── rebuild_to_step2.py
└── verify_package.py
```

## Ai làm gì?

- **Nam (STEP 1):** từ CSV/README/rulebook/calendar làm sạch và chuyển dữ liệu, xuất schema/rules/SQLite.
- **Nguyên (STEP 2):** từ `questions.jsonl` + kết quả Nam, hiểu câu hỏi và xuất `converted_questions.jsonl`.
- **Nhân (sau STEP 2):** nhận **6 file trong `HANDOFF_AFTER_STEP2/`**. Nhân tự dựng prompt và chạy Qwen trong workspace riêng; không có file STEP 3 bàn giao trong ZIP.

## Input gốc chính xác

1. `train/data/biz_101/ban_hang.csv`: bảng bán hàng của riêng biz_101.
2. `train/data/biz_101/README.md`: mô tả cột/đơn vị riêng business.
3. `train/rulebook.md`: luật nghiệp vụ cấp train split.
4. `train/calendar.csv`: lịch và context thời gian.
5. `train/questions.jsonl`: 3.000 câu của cả split; STEP 1 lọc ra 40 câu của biz_101.

`train_biz101_no_labels.zip` là bản thu nhỏ của `train.zip` gốc, giữ **nguyên nội dung bytes** 5 nguồn ở trên. Mọi đáp án train, ground-truth, SQL tham chiếu đều không có trong gói, nhằm hạn chế leakage.

**Chú ý:** Đây là dữ liệu của `train/biz_101`; khi tích hợp `public_test`, phải nạp rulebook/calendar/README tương ứng của split và business đó, không tự dùng lại rulebook train.

## Handoff sau STEP 2

Bắt buộc:
- `converted_questions.jsonl`: 10 converted records; giữ `question_id`, `business_id`, `original_question`, `normalized_question`, intent, thời gian, rule IDs, ambiguities.
- `schema.json`, `business_rules.json`: giải thích bảng/cột và các quy tắc áp dụng, có evidence.
- `database/biz_101.sqlite`: chỉ executor cần, không đưa bytes vào model input.

Khuyến nghị đi kèm: `data_dictionary.md` (để debug) và `converted_question.schema.json` (để validation).

## Chạy lại trên Windows PowerShell (Python >= 3.10)

Tại thư mục gốc sau giải nén:

```powershell
python --version
python .\verify_package.py
python .\rebuild_to_step2.py
python .\verify_package.py
```

Không cần GPU, Docker, API, Internet hay Python packages ngoài chuẩn để dựng lại hai bước này. Các file đã được build sẵn, có thể đọc trực tiếp mà không phải chạy rebuild.

**Lưu ý về generalization:** Converter trong package đang chứa 10 phân tích thủ công cho mẫu `biz_101` — không giả vờ là thuật toán converter chung cho tất cả doanh nghiệp. Khi Nam/Nguyên hoàn thiện pipeline tự động, nên thay code dưới 01/02 và duy trì giao diện 6 file trong `HANDOFF_AFTER_STEP2/`.

**Đã làm:** Data profiling, schema, rules, 10 câu đã converter, reproducibility/consistency checks. **Chưa làm:** Qwen inference, SQL execution benchmark, đo accuracy, train/distillation.
