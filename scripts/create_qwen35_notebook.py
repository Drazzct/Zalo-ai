import json
from pathlib import Path

def create_notebook():
    nb = {
        "nbformat": 4,
        "nbformat_minor": 2,
        "metadata": {
            "colab": {
                "provenance": [],
                "gpuType": "T4"
            },
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3"
            },
            "language_info": {
                "name": "python"
            },
            "accelerator": "GPU"
        },
        "cells": []
    }

    def md(source):
        lines = [line + "\n" for line in source.strip().split("\n")]
        return {"cell_type": "markdown", "metadata": {}, "source": lines}

    def code(source):
        lines = [line + "\n" for line in source.strip().split("\n")]
        return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines}

    # Cell 1: Header
    nb["cells"].append(md("""# 🧠 DataMate: Qwen 3.5 9B with Step-by-Step Reasoning (Chain-of-Thought) & Code Logger

Notebook này được thiết kế chuyên biệt để:
1. **Chạy mô hình Qwen 3.5 9B** trên Google Colab GPU (Tesla T4 15GB VRAM) với Ollama tối ưu song song 4 luồng.
2. **Kích hoạt cơ chế Suy luận Logic (Chain-of-Thought / Reasoning)**: Model bắt buộc suy luận qua thẻ `<reasoning> ... </reasoning>` trước khi sinh code Python `solve(con)`.
3. **Thực thi Benchmark tự động**: Đánh giá trên tập dữ liệu SME của Zalo AI DataMate.
4. **Log chi tiết toàn bộ Code & Suy luận (Code & Reasoning Inspector)**: Trực quan hóa từng câu hỏi gồm Reasoning, Code sinh ra, Kết quả Sandbox và So sánh Ground Truth (Pass/Fail).

> ⚠️ **LƯU Ý:** Hãy đảm bảo bạn đã chọn **Runtime -> Change runtime type -> Hardware accelerator: T4 GPU** trước khi bắt đầu!"""))

    # Cell 2: GPU Check
    nb["cells"].append(md("## 1. Kiểm tra Môi trường & GPU (Tesla T4)"))
    nb["cells"].append(code("!nvidia-smi"))

    # Cell 3: Setup Codebase
    nb["cells"].append(md("""## 2. Thiết lập Mã nguồn Dự án trên Colab (Tự động Clone / Pull từ GitHub)
Tự động clone hoặc kéo code mới nhất từ repository `https://github.com/Drazzct/Zalo-ai.git`."""))
    nb["cells"].append(code("""import os

REPO_URL = "https://github.com/Drazzct/Zalo-ai.git"
TARGET_DIR = "/content/Zalo-ai"

if os.path.exists("/content"):
    # Đang chạy trên Google Colab
    if not os.path.exists(TARGET_DIR):
        print(f"📦 Đang clone mã nguồn mới nhất từ {REPO_URL}...")
        !git clone {REPO_URL} {TARGET_DIR}
    else:
        print(f"🔄 Thư mục {TARGET_DIR} đã tồn tại, đang tự động đồng bộ (git pull) bản mới nhất từ GitHub...")
        %cd {TARGET_DIR}
        !git fetch origin main && git reset --hard origin/main
    %cd {TARGET_DIR}
else:
    # Đang chạy trên máy local
    print(f"ℹ️ Đang chạy trên môi trường local: {os.getcwd()}")
    try:
        !git pull origin main
    except Exception:
        pass

print("✅ Thư mục làm việc hiện tại:", os.getcwd())
!git log -1 --oneline"""))

    # Cell 4: Dependencies
    nb["cells"].append(md("## 3. Cài đặt các thư viện Python"))
    nb["cells"].append(code("!pip install -q pandas duckdb openpyxl pydantic pytest requests openai tabulate"))

    # Cell 5: Setup Ollama
    nb["cells"].append(md("""## 4. Cài đặt & Khởi động Ollama GPU (Tối ưu 4 luồng song song)
Cấu hình `OLLAMA_NUM_PARALLEL=4` và `OLLAMA_FLASH_ATTENTION=1` để tận dụng 100% sức mạnh Tesla T4 GPU."""))
    nb["cells"].append(code("""import subprocess, os, time, urllib.request

# 1. Cài đặt công cụ giải nén zstd và Ollama
if subprocess.run(["which", "ollama"], capture_output=True).returncode != 0:
    print("📦 Đang cài đặt zstd...")
    !sudo apt-get update && sudo apt-get install -y zstd
    print("📦 Đang cài đặt Ollama...")
    !curl -fsSL https://ollama.com/install.sh | sh
else:
    print("✅ Ollama đã được cài đặt sẵn.")

# 2. Khởi chạy Ollama daemon với GPU
env = os.environ.copy()
env["CUDA_VISIBLE_DEVICES"] = "0"
env["OLLAMA_NUM_PARALLEL"] = "4"
env["OLLAMA_FLASH_ATTENTION"] = "1"

try:
    urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
    print("✅ Ollama daemon đã sẵn sàng!")
except Exception:
    print("🚀 Đang khởi động Ollama daemon...")
    with open("ollama.log", "w") as f:
        subprocess.Popen(["ollama", "serve"], env=env, stdout=f, stderr=f)
    time.sleep(5)
    print("✅ Khởi động Ollama daemon thành công!")

# 3. Tải model Qwen 3.5 9B (hoặc chuyển sang qwen2.5-coder:7b tùy chọn)
MODEL_NAME = "qwen3.5:9b"
print(f"📦 Đang tải model {MODEL_NAME} về GPU (khoảng ~5.5GB)...")
!ollama pull {MODEL_NAME}
!ollama ps"""))

    # Cell 6: Warm-up
    nb["cells"].append(md("""### 4.1. Warm-up Model vào VRAM GPU (Bắt buộc)
Chạy một câu ngắn để nạp hoàn toàn trọng số model vào VRAM GPU (Tesla T4). Bảng `ollama ps` phải báo **100% GPU**."""))
    nb["cells"].append(code("""# Kích hoạt model nạp vào VRAM
!ollama run {MODEL_NAME} "print('ready')" --verbose

# Kiểm tra bảng trạng thái VRAM GPU
!ollama ps"""))

    # Cell 7: Demo Single Question with Reasoning
    nb["cells"].append(md("""## 5. Thử nghiệm Đơn lẻ: Xem Trực tiếp Reasoning & Code Sinh ra
Trước khi chạy hàng loạt, hãy chạy thử 1 câu hỏi từ tập `train` để xem model Qwen 3.5 9B suy luận từng bước thế nào."""))
    nb["cells"].append(code("""from pathlib import Path
import json
from src.agent_pipeline import ReasoningPipeline, extract_reasoning, extract_python_code
from src.llm_client import OllamaClient
from IPython.display import display, Markdown

# Khởi tạo Pipeline với Reasoning BẬT (enable_reasoning=True)
llm = OllamaClient(model_name=MODEL_NAME, host="http://127.0.0.1:11434")
pipeline = ReasoningPipeline(
    rulebook_path=Path("train/rulebook.md"),
    calendar_path=Path("train/calendar.csv"),
    llm_client=llm,
    sandbox_timeout=10.0,
    max_retries=2,
    enable_reasoning=True  # KÍCH HOẠT REASONING
)

# Lấy câu hỏi đầu tiên của tập train
with open("train/questions.jsonl", "r", encoding="utf-8") as f:
    sample_q = json.loads(f.readline())

biz_dir = Path("train/data") / sample_q["business_id"]
print(f"📌 Câu hỏi ID: {sample_q['id']} | Shop: {sample_q['business_id']}")
print(f"💬 Nội dung: {sample_q['question']}")
print(f"📅 As of date: {sample_q.get('as_of_date')}")
print("-" * 60)

# Thực thi pipeline và ghi log vào result/single_demo
demo_ans = pipeline.solve_question(sample_q, biz_dir, log_dir=Path("result/single_demo"))

# Đọc log chi tiết vừa ghi ra
with open(f"result/single_demo/{sample_q['id']}.json", "r", encoding="utf-8") as f:
    demo_log = json.load(f)

trace = demo_log["trace"][-1]
reasoning_text = trace.get("reasoning") or trace.get("raw_response") or "Không có reasoning (model không sinh thẻ reasoning hoặc bị lỗi)"
code_text = trace.get("code") or "# Không có code sinh ra"
exec_error = trace.get("exec_error") or "None"

display(Markdown(f\"\"\"### 💭 BƯỚC SUY LUẬN (REASONING / CHAIN-OF-THOUGHT):
```text
{reasoning_text}
```

### 💻 MÃ NGUỒN PYTHON DUCKDB:
```python
{code_text}
```

### ⚙️ CHI TIẾT THỰC THI:
- **Trạng thái Sandbox:** `{'Thành công' if trace.get('exec_success') else 'Thất bại'}`
- **Lỗi Sandbox (nếu có):** `{exec_error}`
- **Số lần thử (Attempts):** `{len(demo_log.get('trace', []))}`

### ⚡ ĐÁP ÁN CUỐI CÙNG:
- **Return Type:** `{demo_ans.get('type')}`
- **Answer:** `{demo_ans.get('answer', demo_ans.get('reason'))}`
- **Thời gian chạy:** `{demo_log.get('elapsed_seconds')}s`
\"\"\"))"""))

    # Cell 8: Benchmark Runner
    nb["cells"].append(md("""## 6. Chạy Benchmark Hàng Loạt với `--reasoning`
Thiết lập số lượng câu hỏi để chạy thử nghiệm benchmark song song 4 luồng trên GPU."""))
    nb["cells"].append(code("""# CẤU HÌNH BENCHMARK
SAMPLE_SIZE = 10       # Đổi thành 50, 100 hoặc để None nếu muốn chạy toàn bộ tập train
WORKERS = 4            # 4 luồng song song tối ưu cho T4 GPU
OUTPUT_FILE = "result/submission_qwen35.jsonl"
LOG_DIR = "result/logs_qwen35"

limit_flag = f"--limit {SAMPLE_SIZE}" if SAMPLE_SIZE else ""

!python scripts/run_benchmark.py \\
  --split-dir train \\
  --model-backend ollama \\
  --model-name {MODEL_NAME} \\
  --workers {WORKERS} \\
  {limit_flag} \\
  --reasoning \\
  --log-dir {LOG_DIR} \\
  --output {OUTPUT_FILE} \\
  --evaluate"""))

    # Cell 9: Detailed Code & Reasoning Inspector
    nb["cells"].append(md("""## 7. 🔍 TRÌNH HIỂN THỊ LOG CODE & SUY LUẬN (Code & Reasoning Inspector)
Xem chi tiết từng câu hỏi: văn bản câu hỏi, toàn bộ reasoning, code Python được sinh, kết quả thực thi và so sánh đúng/sai với Ground Truth."""))
    nb["cells"].append(code("""import json, glob
import pandas as pd
from pathlib import Path
from IPython.display import display, Markdown

# Tải Ground Truth để đối chiếu
gt_map = {}
if os.path.exists("train/ground_truth.jsonl"):
    with open("train/ground_truth.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                gt_map[item["id"]] = item

# Đọc câu hỏi gốc
q_map = {}
with open("train/questions.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            item = json.loads(line)
            q_map[item["id"]] = item

def inspect_question_trace(qid, log_dir="result/logs_qwen35"):
    log_file = Path(log_dir) / f"{qid}.json"
    if not log_file.exists():
        print(f"❌ Không tìm thấy file log cho câu hỏi {qid}")
        return
        
    with open(log_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    q_info = q_map.get(qid, {})
    gt_info = gt_map.get(qid, {})
    pred = data["final_answer"]
    traces = data.get("trace", [])
    last_trace = traces[-1] if traces else {}
    
    reasoning = last_trace.get("reasoning", "Trống")
    code = last_trace.get("code", "Trống")
    exec_success = last_trace.get("exec_success", False)
    exec_error = last_trace.get("exec_error", "")
    
    # Kiểm tra đúng sai
    gt_val = gt_info.get("answer", gt_info.get("reason", "N/A"))
    pred_val = pred.get("answer", pred.get("reason", "N/A"))
    
    is_match = False
    if str(pred_val).strip() == str(gt_val).strip():
        is_match = True
    elif isinstance(pred_val, (int, float)) and isinstance(gt_val, (int, float)):
        if abs(float(pred_val) - float(gt_val)) <= 0.05:
            is_match = True
            
    status_icon = "✅ CHÍNH XÁC (MATCH)" if is_match else "❌ CHƯA KHỚP (MISMATCH)"
    
    md_content = f\"\"\"---
### 📋 Câu hỏi: `{qid}` ({q_info.get('business_id')}) - {status_icon}
- **Nội dung:** {q_info.get('question')}
- **As of date:** `{q_info.get('as_of_date')}` | **Elapsed:** `{data.get('elapsed_seconds')}s`
- **Dự đoán của Model:** `{pred.get('type')}` -> `{pred_val}`
- **Ground Truth:** `{gt_info.get('type')}` -> `{gt_val}`

#### 💭 BƯỚC SUY LUẬN (REASONING):
```text
{reasoning}
```

#### 💻 MÃ NGUỒN PYTHON DUCKDB ĐÃ SINH:
```python
{code}
```

#### ⚙️ TRẠNG THÁI SANDBOX:
- Thành công: `{exec_success}` | Lỗi (nếu có): `{exec_error if exec_error else 'None'}`
\"\"\"
    display(Markdown(md_content))

# Lấy danh sách các câu đã được log
log_files = sorted(glob.glob("result/logs_qwen35/*.json"))
print(f"📊 Đã tìm thấy {len(log_files)} file logs trong result/logs_qwen35/\\n")

# Hiển thị 5 câu đầu tiên làm mẫu
for lf in log_files[:5]:
    qid = Path(lf).stem
    inspect_question_trace(qid)"""))

    # Cell 10: Benchmark Summary DataFrame & CSV Export
    nb["cells"].append(md("""## 8. Bảng Tổng Hợp Chi Tiết & Phân Tích Hiệu Suất
Tổng hợp toàn bộ kết quả vào một DataFrame của Pandas và xuất ra file CSV."""))
    nb["cells"].append(code("""import pandas as pd
import json, glob
from pathlib import Path

rows = []
log_files = sorted(glob.glob("result/logs_qwen35/*.json"))

for lf in log_files:
    with open(lf, "r", encoding="utf-8") as f:
        d = json.load(f)
    qid = d["id"]
    q_item = q_map.get(qid, {})
    gt_item = gt_map.get(qid, {})
    pred = d["final_answer"]
    last_tr = d.get("trace", [{}])[-1]
    
    gt_type = gt_item.get("type", "")
    gt_ans = gt_item.get("answer", gt_item.get("reason", ""))
    pred_type = pred.get("type", "")
    pred_ans = pred.get("answer", pred.get("reason", ""))
    
    # Tính điểm
    match = False
    if pred_type == gt_type:
        if str(pred_ans).strip() == str(gt_ans).strip():
            match = True
        elif isinstance(pred_ans, (int, float)) and isinstance(gt_ans, (int, float)):
            if abs(float(pred_ans) - float(gt_ans)) <= 0.05:
                match = True
                
    has_reasoning = bool(last_tr.get("reasoning", "").strip())
    
    rows.append({
        "question_id": qid,
        "business_id": q_item.get("business_id", ""),
        "question": q_item.get("question", ""),
        "pred_type": pred_type,
        "pred_answer": pred_ans,
        "gt_type": gt_type,
        "gt_answer": gt_ans,
        "is_correct": match,
        "has_reasoning": has_reasoning,
        "elapsed_sec": d.get("elapsed_seconds", 0.0),
        "sandbox_error": last_tr.get("exec_error", "")
    })

df_report = pd.DataFrame(rows)

# In thống kê tổng hợp
total = len(df_report)
correct = df_report["is_correct"].sum()
accuracy = (correct / total * 100) if total > 0 else 0
reasoning_count = df_report["has_reasoning"].sum()

print("=" * 60)
print(f"📊 BÁO CÁO BENCHMARK QWEN 3.5 9B (REASONING)")
print(f"- Tổng số câu kiểm tra: {total}")
print(f"- Số câu đúng: {correct}/{total} ({accuracy:.1f}%)")
print(f"- Số câu có sinh Reasoning hợp lệ: {reasoning_count}/{total} ({reasoning_count/total*100:.1f}%)")
print(f"- Thời gian trung bình mỗi câu: {df_report['elapsed_sec'].mean():.2f} giây")
print("=" * 60)

# Xuất ra file CSV
output_csv = "result/qwen35_reasoning_benchmark_report.csv"
df_report.to_csv(output_csv, index=False, encoding="utf-8-sig")
print(f"✅ Đã lưu báo cáo chi tiết vào: {output_csv}")

# Hiển thị 10 dòng đầu của bảng
display(df_report[["question_id", "business_id", "pred_type", "pred_answer", "gt_answer", "is_correct", "has_reasoning", "elapsed_sec"]].head(10))"""))

    # Cell 11: Tips & Comparison
    nb["cells"].append(md("""## 9. 💡 Hướng dẫn & Đánh giá Chiến lược
### So sánh Đối đầu (A/B Comparison):
- **Qwen2.5-Coder 7B (Không có reasoning):** Tốc độ nhanh nhưng dễ nhầm lẫn giữa bảng `don_hang` và `chi_tiet_don_hang`, hoặc quên lọc đơn hủy bằng Tiếng Việt có dấu.
- **Qwen 3.5 9B (Kèm Reasoning CoT):** Khối `<reasoning>` ép mô hình phải "nghĩ trước khi làm", rà soát toàn bộ schema và as_of_date trước khi viết SQL. Điều này đặc biệt hiệu quả với các câu hỏi phức tạp (tính tỷ lệ huỷ, tìm sản phẩm bán chạy nhất, hoặc nhận biết kỳ dữ liệu không tồn tại để trả về `unanswerable`).

> 🚀 **Mẹo:** Bạn có thể thay đổi `MODEL_NAME = "qwen2.5-coder:7b"` ở mục 4 để chạy lại benchmark và so sánh điểm số trực tiếp giữa 2 kiến trúc!"""))

    # Write notebook file
    out_path = Path("notebooks/qwen35_9b_reasoning_benchmark.ipynb")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    print(f"✅ Đã tạo thành công notebook tại: {out_path} ({len(nb['cells'])} cells)")

if __name__ == "__main__":
    create_notebook()
