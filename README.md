# Zalo AI Challenge — DataMate Agent

Hệ thống Agent AI tự động phân tích và trả lời câu hỏi nghiệp vụ kinh doanh của các doanh nghiệp vừa và nhỏ Việt Nam (SMEs) dựa trên kiến trúc **Code-as-Reasoning (Program-Aided Language Model - PAL)** kết hợp công cụ phân tích dữ liệu hiệu năng cao **DuckDB** và cơ chế bảo hiểm điểm số **Risk-Calibrated Abstention**.

---

## 🚀 Hướng Dẫn Cài Đặt

### 1. Yêu cầu hệ thống
- Python 3.10 trở lên.
- Đã cài đặt `pip`.

### 2. Cài đặt thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

---

## 🧪 Chạy Kiểm Thử Tự Động (Unit & Integration Tests)

Dự án có sẵn bộ 36 bài kiểm thử bao phủ toàn bộ 4 giai đoạn (Xử lý âm dương lịch, Phân tích rulebook, DuckDB Ingestion, Forward-fill đơn hàng, Sandbox thực thi, Chuẩn hóa 9 định dạng, và Cổng Abstain):

```bash
pytest tests/ -v
```

---

## 🏃 Các Cách Chạy Dự Án

### Cách 1: Chạy kiểm tra nhanh trên một vài câu hỏi (Quick Test)

Chạy thử nghiệm trên 10 câu đầu tiên của tập `train` hoặc `public_test`:

```bash
# Chạy 10 câu của tập train
python predict.py --input-dir train --limit 10 --output submission.jsonl

# Hoặc chạy 10 câu của tập public_test
python predict.py --input-dir public_test --limit 10 --output submission.jsonl
```

Kết quả sẽ sinh ra file `submission.jsonl` và các file log chi tiết cho từng câu hỏi tại thư mục `result/logs/`.

---

### Cách 2: Chạy Benchmark và Đánh giá Điểm số (Train Set)

Để chạy kiểm thử kèm tự động chấm điểm so với `answers.jsonl`:

```bash
python scripts/run_benchmark.py --split-dir train --limit 20 --evaluate
```

Kết quả in ra bảng tổng kết điểm thi theo quy chế Zalo AI:
$$\text{Điểm} = \text{Đúng (+1)} - \text{Sai (-1)} + \text{Abstain (0)}$$

---

### Cách 3: Chạy Đánh giá một file kết quả đã có

Nếu bạn đã có sẵn file `submission.jsonl` và muốn chấm điểm với tập nhãn `train/answers.jsonl`:

```bash
python scripts/evaluate_baseline.py --submission submission.jsonl --gt train/answers.jsonl
```

---

### Cách 4: Chạy Phân tích Khám phá Dữ liệu (EDA)

Để quét và trích xuất cấu trúc dữ liệu của toàn bộ 30 doanh nghiệp `train` và 14 doanh nghiệp `public_test`:

```bash
python scripts/run_eda.py
```
Báo cáo chi tiết sẽ được lưu tại `reports/eda_summary.json`.

---

## 🐳 Chạy Theo Chuẩn Docker Thi Đấu Của BTC

Trong môi trường Docker của BTC Zalo AI, dữ liệu test được mount tại `/data` và kết quả ghi tại `/result/submission.jsonl`:

```bash
# Chạy script dự đoán chuẩn thi đấu
bash predict.sh
```
Hoặc qua Docker:
```bash
docker run --rm \
  -v $(pwd)/public_test:/data \
  -v $(pwd)/result:/result \
  datamate-agent:latest
```

---

## 📂 Cấu Trúc Dự Án

```
Zalo-ai/
├── src/
│   ├── calendar_resolver.py   # Tra cứu âm lịch, Tết, tính khoảng thời gian tuần/tháng
│   ├── rulebook_parser.py     # Đọc động rulebook.md, trích xuất luật theo ngành
│   ├── data_ingestor.py       # DuckDB Ingestion: forward-fill, sửa lệch header, lọc footer
│   ├── schema_profiler.py     # Trích xuất metadata, min/max date, quy đổi đơn vị README
│   ├── query_normalizer.py    # Chuẩn hóa teencode & neo mốc thời gian ISO
│   ├── sandbox.py             # Môi trường thực thi code Python/DuckDB an toàn kèm timeout
│   ├── prompt_generator.py    # Master Prompt & Self-reflection prompt generator
│   ├── type_formatter.py      # Ép kiểu nghiêm ngặt cho 9 loại đáp án theo Rule 9
│   ├── abstain_gate.py        # Cổng bảo vệ điểm số, tránh bị trừ -1 điểm
│   ├── agent_pipeline.py      # Pipeline Reasoner tích hợp hoàn chỉnh
│   └── evaluator.py           # Bộ chấm điểm chuẩn của cuộc thi (+1, -1, 0)
├── scripts/
│   ├── run_eda.py             # Quét toàn bộ dữ liệu 44 cửa hàng
│   ├── run_benchmark.py       # Chạy benchmark hàng loạt và xuất submission
│   └── evaluate_baseline.py   # Đánh giá submission với ground truth
├── tests/                     # 36 unit/integration tests
├── predict.py                 # File entry point chạy suy luận
├── predict.sh                 # File bash script chuẩn thi đấu theo Rule của BTC
├── requirements.txt           # Danh mục thư viện Python cần cài
└── README.md                  # Tài liệu hướng dẫn sử dụng
```

