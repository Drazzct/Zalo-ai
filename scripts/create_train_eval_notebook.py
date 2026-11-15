import json
from pathlib import Path


def create_train_eval_notebook():
  nb = {
      "nbformat": 4,
      "nbformat_minor": 2,
      "metadata": {
          "colab": {"provenance": [], "gpuType": "T4"},
          "kernelspec": {"name": "python3", "display_name": "Python 3"},
          "language_info": {"name": "python"},
          "accelerator": "GPU",
      },
      "cells": [],
  }

  def md(source):
    lines = [line + "\n" for line in source.strip().split("\n")]
    return {"cell_type": "markdown", "metadata": {}, "source": lines}

  def code(source):
    lines = [line + "\n" for line in source.strip().split("\n")]
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines,
    }

  # Cell 1: Header
  nb["cells"].append(
      md("""# 🎯 Zalo AI Challenge 2026: DataMate - Train Set Evaluation & Accuracy Benchmark
*(Tối ưu chạy trên **Google Colab (GPU T4 / A100)** và **Kaggle Notebooks (GPU T4 x 2 / P100)**)*

Notebook này được thiết kế chuyên biệt để:
1. **Đánh giá & Chấm điểm Trực tiếp trên tập Train (`train/`)**: So sánh từng câu hỏi với đáp án chuẩn (`train/answers.jsonl`) theo công thức chính thức của BTC Zalo AI: **Đúng (+1đ), Sai (-1đ), Abstain (0đ)**.
2. **Mô hình Qwen 3.5 9B with Reasoning (`qwen3.5:9b`)**: Tận dụng cơ chế Chain-of-Thought qua thẻ `<reasoning>` giúp mô hình tư duy trước khi sinh mã DuckDB Python.
3. **Pre-warming DuckDB & Chạy Đa Luồng Song Song (2 Workers)**: Tải sẵn dữ liệu vào RAM, tăng tốc độ xử lý lên gấp 10 lần.
4. **Hỗ trợ Tự Động Resume**: Nếu bị ngắt kết nối giữa chừng, chỉ cần chạy lại là hệ thống tự động làm tiếp các câu còn lại.
5. **Trực quan hóa Suy luận & Mã nguồn (Code & Reasoning Inspector)**: Xem chi tiết từng câu hỏi gồm Reasoning CoT, Code DuckDB sinh ra, Kết quả Sandbox và Đối soát Ground Truth (Pass/Fail).
6. **Bảng Báo Cáo DataFrame & Lọc Danh Sách Câu Sai**: Xuất file CSV phân tích chi tiết các ca sai để tinh chỉnh prompt/quy tắc nghiệp vụ.

---
### ⚙️ HƯỚNG DẪN CẤU HÌNH PHẦN CỨNG:
- **Trên Google Colab:** Vào menu **Runtime -> Change runtime type -> Hardware accelerator: T4 GPU** (hoặc A100).
- **Trên Kaggle Notebooks:** Ở thanh menu bên phải:
  - **Accelerator:** Chọn **GPU T4 x 2** (hoặc **GPU P100**).
  - **Internet:** BẮT BUỘC gạt sang **"Internet on"**.""")
  )

  # Cell 2: Check Environment & GPU
  nb["cells"].append(
      md("## 1. Kiểm tra Môi trường, GPU & Kết nối Google Drive")
  )
  nb["cells"].append(
      code("""import os, sys, urllib.request

# 1. Nhận diện môi trường chạy
if os.path.exists("/kaggle"):
    ENV = "kaggle"
    print("🚀 Môi trường phát hiện: KAGGLE NOTEBOOK (/kaggle/working)")
    OUTPUT_DIR = "/kaggle/working/result"
elif os.path.exists("/content"):
    ENV = "colab"
    print("🚀 Môi trường phát hiện: GOOGLE COLAB (/content)")
    OUTPUT_DIR = "result"
else:
    ENV = "local"
    print(f"🚀 Môi trường phát hiện: LOCAL ({os.getcwd()})")
    OUTPUT_DIR = "result"

# 2. Tự động Mount Google Drive trên Google Colab để lưu kết quả liên tục
if ENV == "colab":
    try:
        from google.colab import drive
        drive.mount('/content/drive')
        OUTPUT_DIR = "/content/drive/MyDrive/zalo_datamate_train"
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        print(f"📁 Google Drive đã kết nối thành công! Lưu an toàn tại: {OUTPUT_DIR}")
    except Exception as e:
        print("ℹ️ Chạy không mount Drive, lưu kết quả tại thư mục cục bộ result/:", e)
        OUTPUT_DIR = "result"
        os.makedirs(OUTPUT_DIR, exist_ok=True)
else:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

# 3. Kiểm tra kết nối Internet
try:
    urllib.request.urlopen("https://www.google.com", timeout=3)
    print("🌐 Kết nối Internet: ĐÃ BẬT (OK)")
except Exception:
    if ENV == "kaggle":
        print("⚠️ CẢNH BÁO KAGGLE: Bạn chưa bật Internet! Vào thanh công cụ bên phải -> Settings -> Bật 'Internet on'.")
    else:
        print("⚠️ CẢNH BÁO: Không có kết nối Internet.")

# 4. Kiểm tra GPU
!nvidia-smi""")
  )

  # Cell 3: Setup Codebase
  nb["cells"].append(
      md("""## 2. Thiết lập Mã nguồn Dự án (Tự động Clone / Git Pull)
Tự động kéo phiên bản mới nhất chứa toàn bộ các bản sửa lỗi bảng/cột từ GitHub repository `https://github.com/Drazzct/Zalo-ai.git`.""")
  )
  nb["cells"].append(
      code("""import os

REPO_URL = "https://github.com/Drazzct/Zalo-ai.git"

if os.path.exists("/kaggle"):
    TARGET_DIR = "/kaggle/working/Zalo-ai"
elif os.path.exists("/content"):
    TARGET_DIR = "/content/Zalo-ai"
else:
    TARGET_DIR = os.getcwd()

if not os.path.exists(TARGET_DIR) or not os.path.exists(os.path.join(TARGET_DIR, ".git")):
    print(f"📦 Đang clone mã nguồn mới nhất từ {REPO_URL} vào {TARGET_DIR}...")
    !git clone {REPO_URL} {TARGET_DIR}
else:
    print(f"🔄 Đang tự động đồng bộ (git pull) bản mới nhất từ GitHub...")
    %cd {TARGET_DIR}
    !git fetch origin main && git reset --hard origin/main

%cd {TARGET_DIR}
print("✅ Thư mục làm việc hiện tại:", os.getcwd())
!git log -1 --oneline""")
  )

  # Cell 4: Dependencies
  nb["cells"].append(md("## 3. Cài đặt các thư viện Python"))
  nb["cells"].append(
      code(
          "!pip install -q pandas duckdb openpyxl pydantic pytest requests"
          " openai tabulate"
      )
  )

  # Cell 5: Setup Ollama
  nb["cells"].append(
      md("""## 4. Cài đặt & Khởi động Ollama GPU Daemon
Cấu hình tối ưu GPU VRAM để 100% layers của mô hình `qwen3.5:9b` nằm trọn trong VRAM card Tesla T4/A100.""")
  )
  nb["cells"].append(
      code("""import subprocess, os, time, urllib.request

# 1. Cài đặt Ollama nếu chưa có
if subprocess.run(["which", "ollama"], capture_output=True).returncode != 0:
    print("📦 Đang cài đặt zstd và Ollama...")
    !sudo apt-get update && sudo apt-get install -y zstd
    !curl -fsSL https://ollama.com/install.sh | sh
else:
    print("✅ Ollama đã được cài đặt sẵn.")

# 2. Khởi chạy Ollama daemon với GPU
env = os.environ.copy()
env["CUDA_VISIBLE_DEVICES"] = "0"
env["OLLAMA_NUM_PARALLEL"] = "2"
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

# 3. Tải mô hình Qwen 3.5 9B with Reasoning
MODEL_NAME = "qwen3.5:9b"
print(f"📦 Đang tải và kiểm tra mô hình: {MODEL_NAME}...")
!ollama pull {MODEL_NAME}

# 4. Tùy chỉnh Modelfile tối ưu VRAM (Khóa Context 4096 tokens)
modelfile_content = f\"\"\"FROM {MODEL_NAME}
PARAMETER temperature 0.0
PARAMETER num_ctx 4096
PARAMETER num_predict 1536
\"\"\"
with open("Modelfile", "w") as f:
    f.write(modelfile_content)

!ollama create qwen3.5:9b-optimized -f Modelfile
print("✅ Mô hình qwen3.5:9b-optimized đã sẵn sàng chạy!")""")
  )

  # Cell 6: Run Benchmark Evaluation
  nb["cells"].append(
      md("""## 5. Chạy Benchmark Đánh giá trên Tập Train
Thiết lập số lượng câu hỏi cần chạy. Bạn có thể chọn chạy thử nhanh `LIMIT = 50` câu (khoảng 5-8 phút) hoặc để `LIMIT = None` để chạy toàn bộ tập train.""")
  )
  nb["cells"].append(
      code("""import os

# CẤU HÌNH THAM SỐ CHẠY EVALUATION:
LIMIT = 50          # Số lượng câu hỏi muốn kiểm tra (đặt None để chạy toàn bộ tập train)
BIZ_ID = ""         # Lọc theo shop cụ thể (ví dụ "biz_101", "biz_121") hoặc để "" để chạy tất cả
WORKERS = 2         # Số luồng song song (khuyên dùng 2 luồng trên GPU T4)
RESUME = True       # Bật True để tiếp tục từ các câu đã làm trước đó nếu bị ngắt
MODEL = "qwen3.5:9b-optimized"

cmd = [
    "python", "scripts/run_benchmark.py",
    "--split-dir", "train",
    "--output", "result/submission_train.jsonl",
    "--log-dir", "result/logs_train",
    "--evaluate",
    "--model-backend", "ollama",
    "--model-name", MODEL,
    "--workers", str(WORKERS),
]

if LIMIT is not None:
    cmd.extend(["--limit", str(LIMIT)])
if BIZ_ID:
    cmd.extend(["--biz-id", BIZ_ID])
if RESUME:
    cmd.append("--resume")

cmd_str = " ".join(cmd)
print(f"🚀 Đang thực thi lệnh đánh giá:\\n{cmd_str}\\n")
!{cmd_str}""")
  )

  # Cell 7: Official Competition Score Summary
  nb["cells"].append(
      md("""## 6. Bảng Tổng Kết Điểm Số & Đánh Giá Chính Thức (Official Competition Score)
Đối chiếu trực tiếp từng câu trả lời với `train/answers.jsonl` theo chuẩn cuộc thi Zalo AI DataMate.""")
  )
  nb["cells"].append(
      code("""import json
from pathlib import Path
from src.evaluator import Evaluator

def load_jsonl(path):
    records = []
    if not Path(path).exists():
        return records
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

pred_file = Path("result/submission_train.jsonl")
gt_file = Path("train/answers.jsonl")

preds = load_jsonl(pred_file)
gts = load_jsonl(gt_file)

if not preds:
    print("⚠️ Chưa có kết quả trong result/submission_train.jsonl. Vui lòng chạy Cell 5 trước!")
else:
    processed_ids = {p["id"] for p in preds}
    filtered_gt = [g for g in gts if g["id"] in processed_ids]
    
    metrics = Evaluator.evaluate(preds, filtered_gt)
    
    print("=" * 65)
    print("🏆 BẢNG TỔNG KẾT ĐIỂM ĐÁNH GIÁ (TRAIN SET BENCHMARK)")
    print("=" * 65)
    print(f"Tổng số câu đã đánh giá : {metrics['total_questions']}")
    print(f"Số câu ĐÚNG (+1 điểm)   : {metrics['correct']}")
    print(f"Số câu SAI  (-1 điểm)   : {metrics['wrong']}")
    print(f"Số câu BỎ QUA (0 điểm)  : {metrics['abstain']}")
    print("-" * 65)
    print(f"🌟 TỔNG ĐIỂM (SCORE)    : {metrics['total_score']} / {metrics['total_questions']}")
    print(f"🎯 ĐỘ CHÍNH XÁC (ACC)   : {metrics['accuracy']:.2f}%")
    print("=" * 65)
    
    print("\\n📊 CHI TIẾT THEO TỪNG KIỂU ĐÁP ÁN (ANSWER TYPE BREAKDOWN):")
    header = f"{'Kiểu Đáp Án':<15} | {'Tổng':<6} | {'Đúng (+1)':<10} | {'Sai (-1)':<10} | {'Abstain (0)':<12} | {'Tỉ Lệ Đúng':<10}"
    print(header)
    print("-" * len(header))
    for t, s in metrics["type_stats"].items():
        acc = (s['correct'] / s['total'] * 100) if s['total'] > 0 else 0
        print(f"{t:<15} | {s['total']:<6} | {s['correct']:<10} | {s['wrong']:<10} | {s['abstain']:<12} | {acc:>8.1f}%")
    print("=" * 65)""")
  )

  # Cell 8: Code & Reasoning Inspector
  nb["cells"].append(
      md("""## 7. Trực quan hóa Suy luận & Mã nguồn (Code & Reasoning Inspector)
Xem chi tiết từng câu hỏi: suy luận logic CoT bên trong `<reasoning>`, mã Python DuckDB sinh ra, lỗi sandbox (nếu có) và so sánh trực tiếp với đáp án chuẩn.""")
  )
  nb["cells"].append(
      code("""import json, glob
from pathlib import Path
from IPython.display import display, Markdown

# Tải thông tin câu hỏi và đáp án chuẩn để đối chiếu
q_map = {q["id"]: q for q in load_jsonl("train/questions.jsonl")}
gt_map = {g["id"]: g for g in load_jsonl("train/answers.jsonl")}

def inspect_question(qid):
    log_file = Path(f"result/logs_train/{qid}.json")
    if not log_file.exists():
        print(f"Không tìm thấy log cho câu hỏi: {qid}")
        return
        
    with open(log_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    q_info = q_map.get(qid, {})
    gt_info = gt_map.get(qid, {})
    
    pred = data.get("final_answer", {})
    trace = data.get("trace", [])
    last_tr = trace[-1] if trace else {}
    
    reasoning = last_tr.get("reasoning", "(Không có reasoning)")
    code = last_tr.get("code", "(Không sinh được code)")
    exec_success = last_tr.get("exec_success", False)
    exec_error = last_tr.get("exec_error", "")
    
    # Đối chiếu Pass / Fail / Abstain
    gt_type = gt_info.get("type", "")
    gt_val = gt_info.get("answer", gt_info.get("reason", ""))
    pred_type = pred.get("type", "")
    pred_val = pred.get("answer", pred.get("reason", ""))
    
    if pred_type == "abstain":
        status_badge = "⚪ **ABSTAIN (0 ĐIỂM)**"
    elif pred_type == gt_type and str(pred_val).strip() == str(gt_val).strip():
        status_badge = "✅ **CHÍNH XÁC (+1 ĐIỂM)**"
    elif pred_type == gt_type and isinstance(pred_val, (int, float)) and isinstance(gt_val, (int, float)) and abs(float(pred_val) - float(gt_val)) <= 0.05:
        status_badge = "✅ **CHÍNH XÁC (+1 ĐIỂM)**"
    else:
        status_badge = "❌ **SAI (-1 ĐIỂM)**"
        
    md_content = f\"\"\"
### 🔍 CHI TIẾT CÂU HỎI: `{qid}` - {status_badge}
- **Cửa hàng:** `{q_info.get('business_id', '')}` | **Ngày mốc (as_of_date):** `{q_info.get('as_of_date', '')}`
- **Câu hỏi:** \"{q_info.get('question', '')}\"
- **Thời gian xử lý:** `{data.get('elapsed_seconds', 0):.2f}s` | **Số lần thử:** `{len(trace)}`
- **Dự đoán Model:** `{pred_type}` -> `{pred_val}`
- **Đáp án Chuẩn (GT):** `{gt_type}` -> `{gt_val}`

#### 💭 BƯỚC SUY LUẬN LOGIC (CHAIN-OF-THOUGHT):
```text
{reasoning}
```

#### 💻 MÃ NGUỒN PYTHON DUCKDB ĐÃ SINH:
```python
{code}
```

#### ⚙️ TRẠNG THÁI SANDBOX:
- **Thành công:** `{exec_success}`
- **Thông báo lỗi (nếu có):** `{exec_error if exec_error else 'None'}`
---
\"\"\"
    display(Markdown(md_content))

# Lấy danh sách 5 câu đầu tiên được ghi log
log_files = sorted(glob.glob("result/logs_train/*.json"))
print(f"📊 Đã tìm thấy {len(log_files)} file logs trong result/logs_train/\\n")

for lf in log_files[:5]:
    inspect_question(Path(lf).stem)""")
  )

  # Cell 9: Detailed DataFrame & Error Analysis
  nb["cells"].append(
      md("""## 8. Bảng Tổng Hợp Chi Tiết Pandas & Phân Tích Lỗi (Error Analysis)
Tổng hợp toàn bộ kết quả vào một DataFrame của Pandas, xuất ra file CSV và hiển thị riêng các câu bị trả lời sai hoặc abstain để xem xét.""")
  )
  nb["cells"].append(
      code("""import pandas as pd
import json, glob
from pathlib import Path

rows = []
log_files = sorted(glob.glob("result/logs_train/*.json"))

for lf in log_files:
    with open(lf, "r", encoding="utf-8") as f:
        d = json.load(f)
    qid = d["id"]
    q_item = q_map.get(qid, {})
    gt_item = gt_map.get(qid, {})
    pred = d.get("final_answer", {})
    trace = d.get("trace", [{}])
    last_tr = trace[-1] if trace else {}
    
    gt_type = gt_item.get("type", "")
    gt_ans = gt_item.get("answer", gt_item.get("reason", ""))
    pred_type = pred.get("type", "")
    pred_ans = pred.get("answer", pred.get("reason", ""))
    
    # Tính điểm
    is_correct = False
    score = 0
    if pred_type == "abstain":
        score = 0
    elif pred_type == gt_type:
        if str(pred_ans).strip() == str(gt_ans).strip():
            is_correct = True
            score = 1
        elif isinstance(pred_ans, (int, float)) and isinstance(gt_ans, (int, float)):
            if abs(float(pred_ans) - float(gt_ans)) <= 0.05:
                is_correct = True
                score = 1
            else:
                score = -1
        else:
            score = -1
    else:
        score = -1
        
    has_reasoning = bool(last_tr.get("reasoning", "").strip())
    
    rows.append({
        "question_id": qid,
        "business_id": q_item.get("business_id", ""),
        "question": q_item.get("question", ""),
        "pred_type": pred_type,
        "pred_answer": pred_ans,
        "gt_type": gt_type,
        "gt_answer": gt_ans,
        "is_correct": is_correct,
        "score": score,
        "has_reasoning": has_reasoning,
        "attempts": len(trace),
        "elapsed_sec": d.get("elapsed_seconds", 0.0),
        "sandbox_error": last_tr.get("exec_error", "")
    })

df_report = pd.DataFrame(rows)

output_csv = "result/train_evaluation_report.csv"
df_report.to_csv(output_csv, index=False, encoding="utf-8-sig")
print(f"✅ Đã lưu báo cáo chi tiết {len(df_report)} câu vào: {output_csv}")

# Hiển thị bảng các câu bị SAI để phân tích nguyên nhân
df_failed = df_report[~df_report["is_correct"]]
print(f"\\n❌ DANH SÁCH CÁC CÂU BỊ SAI HOẶC ABSTAIN ({len(df_failed)} câu):")
if not df_failed.empty:
    display(df_failed[["question_id", "business_id", "pred_type", "pred_answer", "gt_answer", "score", "sandbox_error"]].head(15))
else:
    print("🎉 Toàn bộ các câu kiểm tra đều trả lời ĐÚNG 100%!")""")
  )

  # Cell 10: Zip & Download Results
  nb["cells"].append(
      md("""## 9. Đóng Gói Toàn Bộ Log & Tải Về Máy
Tự động nén toàn bộ log chi tiết vào file zip để tải về máy hoặc lưu trữ.""")
  )
  nb["cells"].append(
      code("""import shutil, os
from pathlib import Path

# 1. Nén thư mục logs_train thành zip
zip_name = "train_evaluation_bundle"
log_dir = "result/logs_train"

if os.path.exists(log_dir):
    shutil.make_archive(zip_name, "zip", "result")
    print(f"📦 Đã tạo file nén: {zip_name}.zip")
    
# 2. Hỗ trợ tải trực tiếp về máy trên Google Colab / Kaggle
try:
    from google.colab import files
    files.download(f"{zip_name}.zip")
    files.download("result/train_evaluation_report.csv")
    print("⬇️ Đã kích hoạt tải file về máy qua Colab.")
except Exception:
    try:
        from IPython.display import FileLink
        display(FileLink(f"{zip_name}.zip"))
        display(FileLink("result/train_evaluation_report.csv"))
        print("🔗 Nhấp vào liên kết trên để tải file về máy.")
    except Exception as e:
        print("File đã lưu tại:", os.path.abspath(f"{zip_name}.zip"))""")
  )

  # Save notebook file
  out_path = Path("notebooks/colab_train_evaluation.ipynb")
  out_path.parent.mkdir(parents=True, exist_ok=True)
  with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

  print(
      f"✅ Đã tạo thành công notebook tại: {out_path} ({len(nb['cells'])} cells)"
  )


if __name__ == "__main__":
  create_train_eval_notebook()
