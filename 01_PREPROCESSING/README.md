# 01 — PREPROCESSING (Nam)

## Input
`../00_RAW_INPUT/train_biz101_no_labels.zip` chứa chính xác 5 file nguồn của split train: CSV bán hàng, README biz_101, rulebook.md, calendar.csv, questions.jsonl. Không có `answers.jsonl`.

## Output
- `biz_101.sqlite`: dữ liệu staging SQLite để thực thi SQL ở bước sau (không đưa toàn bộ DB vào LLM).
- `schema.json`, `schema.sql`: lược đồ và mapping CSV -> SQLite.
- `business_rules.json`: luật nghiệp vụ có tham chiếu nguồn.
- `data_dictionary.md`: định nghĩa các trường, đơn vị, cảnh báo.
- `data_profile.json`, `inventory.json`, `verification.json`: kiểm kê và profiling.
- `benchmark/questions_biz_101.jsonl`: 40 câu hỏi thật để Converter lựa chọn.
- `sources/`: bản sao nguyên gốc 5 file nguồn phục vụ audit.

## Chạy lại
Khuyến nghị chạy từ thư mục **gốc của package**:

```powershell
python .\rebuild_to_step2.py
python .\verify_package.py
```

Nếu chỉ chạy riêng STEP 1 trong thư mục này:

```powershell
python .\analyze_step1.py ..\00_RAW_INPUT\train_biz101_no_labels.zip
python .\finalize_step1.py
```

Lưu ý `finalize_step1.py` kế thừa từ bản audit trước và tự sinh `README.md` / `STEP1_REPORT.md` với một số lời dẫn lịch sử không phù hợp với bản lọc không có answers. Script `rebuild_to_step2.py` tự phục hồi README phiên bản bàn giao và xóa report lịch sử đó sau khi chạy, để tránh mô tả sai.

Không có nhãn, teacher output, Qwen prompt hoặc generated SQL tại bước này.
