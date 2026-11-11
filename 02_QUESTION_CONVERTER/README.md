# 02 — QUESTION CONVERTER (Nguyên)

## Input
- `../01_PREPROCESSING/benchmark/questions_biz_101.jsonl` — 40 câu hỏi thật của biz_101
- `../01_PREPROCESSING/schema.json` — cấu trúc SQLite
- `../01_PREPROCESSING/business_rules.json` — luật nghiệp vụ
- `../01_PREPROCESSING/biz_101.sqlite` — để đối chiếu phạm vi dữ liệu, **không lấy đáp án**

## Output chính
`converted_questions.jsonl` — **10 câu hỏi thật đã được chuẩn hóa** (intent, metric, aggregation, date constraints, filter, rule IDs, ambiguity, provenance).

## Tài liệu phụ trợ
- `converted_question.schema.json`: schema kiểm tra cấu trúc Converter output.
- `converter_mapping.csv`: bảng kiểm mapping theo câu.
- `STEP2_REPORT.md`: nhận xét thủ công từng câu.
- `verification.json`: kết quả kiểm tra converter (không phải accuracy của Qwen).
- `build_step2.py`, `verify_step2.py`, `write_report.py`: code dựng lại và kiểm thử.

## Chạy lại
Tại **thư mục gốc ZIP sau khi giải nén**:

```powershell
python .\rebuild_to_step2.py
python .\verify_package.py
```

**Giới hạn:** `build_step2.py` chứa 10 annotation được đánh giá thủ công cho `biz_101`, chưa phải converter tổng quát cho mọi doanh nghiệp/câu hỏi. Thay implementation của Nguyên sau này, giữ định dạng output nhất quán và rule provenance.

Không có input contract cho Qwen, prompt builder hoặc inference trong gói này.
