"""Generator script to build the vLLM High-Throughput Reasoning Benchmark Notebook.

Generates:
notebooks/qwen35_vllm_reasoning_benchmark.ipynb
"""

import json
from pathlib import Path


def build_vllm_notebook():
  nb = {
      'nbformat': 4,
      'nbformat_minor': 2,
      'metadata': {
          'colab': {'provenance': [], 'gpuType': 'T4'},
          'kernelspec': {'name': 'python3', 'display_name': 'Python 3'},
          'language_info': {'name': 'python'},
          'accelerator': 'GPU',
      },
      'cells': [],
  }

  def md(source):
    lines = [line + '\n' for line in source.strip().split('\n')]
    return {'cell_type': 'markdown', 'metadata': {}, 'source': lines}

  def code(source):
    lines = [line + '\n' for line in source.strip().split('\n')]
    return {
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': lines,
    }

  # Cell 1: Header
  nb['cells'].append(
      md("""# 🚀 Zalo AI Challenge 2026: DataMate - Qwen 3.5 9B Reasoning with vLLM Ultra-Fast Runner
*(Tối ưu hóa tốc độ suy luận mô hình **Qwen 3.5 9B (Reasoning)** bằng **vLLM (PagedAttention & Continuous Batching)** trên **Kaggle (2x T4 / P100)** và **Google Colab (T4 / A100)**)*

### 🌟 Ưu điểm vượt trội của bản vLLM Qwen 3.5 9B:
1. **Mô hình Qwen 3.5 9B Reasoning**: Sử dụng kiến trúc suy luận thế hệ mới `Qwen/Qwen3.5-9B`, hỗ trợ suy luận logic qua thẻ `<reasoning>` trước khi sinh mã Python.
2. **Tốc độ thông lượng gấp 3 - 5 lần**: vLLM quản lý KV-cache thông qua PagedAttention và gom batch liên tục (continuous batching), cho phép chạy **4 luồng song song** mà không làm tăng đáng kể độ trễ.
3. **Hỗ trợ Tensor Parallelism (TP=2) trên Kaggle**: Tự động tận dụng cùng lúc cả 2 card GPU T4 trên Kaggle (`tp=2`) để chia tải mô hình 9B (mỗi card ~9GB VRAM), tối ưu hoá tốc độ sinh token và chống tràn VRAM.
4. **Cơ chế Fast-Retry & Chống nghẽn Timeout**: Tự động bắt timeout (90s) và retry tức thì không qua reasoning, đảm bảo không bị kẹt ở các câu tính toán phức tạp.
5. **Schema Trimming & Strict Reasoning**: Rút gọn schema context hơn 70%, kiềm chế reasoning dưới 40 từ giúp ngăn chặn 100% hiện tượng tràn context / truncation.
6. **Auto-Resume & Lưu Google Drive**: Bảo toàn tiến độ làm bài khi mất kết nối mạng hoặc hết phiên Colab.

---
### ⚙️ HƯỚNG DẪN CẤU HÌNH PHẦN CỨNG:
- **Trên Kaggle Notebooks:** Ở thanh menu bên phải:
  - **Accelerator:** BẮT BUỘC chọn **GPU T4 x 2** (để kích hoạt Tensor Parallelism 2 card chia tải mô hình 9B) hoặc **GPU P100**.
  - **Internet:** BẮT BUỘC gạt sang **"Internet on"** (để tải thư viện và mô hình từ HuggingFace).
- **Trên Google Colab:** Vào menu **Runtime -> Change runtime type -> Hardware accelerator: T4 GPU** (hoặc A100).""")
  )

  # Cell 2: Environment & GPU Check + Google Drive Mount
  nb['cells'].append(
      md("""## 1. Kiểm tra Môi trường, GPU & Kết nối Google Drive
Nhận diện nền tảng Kaggle / Colab và mount Google Drive để lưu kết quả liên tục theo thời gian thực.""")
  )
  nb['cells'].append(
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
        OUTPUT_DIR = "/content/drive/MyDrive/zalo_datamate"
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
import shutil

if shutil.which("nvidia-smi"):
    !nvidia-smi
else:
    print("❌ CẢNH BÁO: KHÔNG TÌM THẤY GPU (Đang chạy ở chế độ CPU Only)!")
    if ENV == "kaggle":
        print("👉 CÁCH BẬT GPU TRÊN KAGGLE:")
        print("   1. Nhìn sang thanh công cụ bên phải màn hình (Session options).")
        print("   2. Tại mục 'Accelerator', bấm vào và chọn 'GPU T4 x 2'.")
        print("   3. Xác nhận khởi động lại session để kích hoạt GPU!")
    elif ENV == "colab":
        print("👉 CÁCH BẬT GPU TRÊN COLAB:")
        print("   1. Vào menu 'Runtime' -> 'Change runtime type'.")
        print("   2. Tại mục 'Hardware accelerator', chọn 'T4 GPU'.")
        print("   3. Bấm 'Save' để kích hoạt GPU!")
    raise RuntimeError("❌ DỪNG LẠI: Chưa bật GPU! vLLM không thể chạy trên CPU. Hãy bật GPU theo hướng dẫn trên rồi chạy lại!")""")
  )

  # Cell 3: Clone or Pull Codebase
  nb['cells'].append(
      md("""## 2. Thiết lập Mã nguồn Dự án (Tự động Clone / Git Pull)
Đồng bộ phiên bản mới nhất từ repository `https://github.com/Drazzct/Zalo-ai.git`.""")
  )
  nb['cells'].append(
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

  # Cell 4: Install Dependencies including vLLM
  nb['cells'].append(
      md("""## 3. Cài đặt các thư viện Python & vLLM Engine
Cài đặt vLLM cùng DuckDB, OpenPyXL, Pandas và các phụ thuộc phục vụ suy luận dữ liệu.""")
  )
  nb['cells'].append(
      code("""!pip install -q --no-warn-conflicts vllm pandas duckdb openpyxl pydantic pytest requests openai tabulate""")
  )

  # Cell 5: Setup & Launch vLLM OpenAI-Compatible Server
  nb['cells'].append(
      md("""## 4. Khởi động vLLM Server (Qwen 3.5 9B Reasoning Engine)
Khởi chạy tiến trình `vllm.entrypoints.openai.api_server` ở nền:
- **Mô hình**: `Qwen/Qwen3.5-9B` (đăng ký alias `qwen3.5:9b` tương thích pipeline).
- **Reasoning**: Hỗ trợ suy luận logic qua thẻ `<reasoning>` trước khi sinh mã Python.
- **Tensor Parallelism**: Tự động đặt `tp=2` nếu phát hiện 2 GPU trên Kaggle (chia tải ~9GB VRAM/card).
- **Port**: 8000 (`http://127.0.0.1:8000/v1`).
- **Max Model Len**: 4096 tokens (tiết kiệm VRAM cho 4 workers gom batch).
- **Enforce Eager**: Tối ưu hóa thời gian khởi động trên kiến trúc GPU T4.""")
  )
  nb['cells'].append(
      code("""import subprocess, os, sys, time, urllib.request, json
import torch, shutil

# 1. Kiểm tra phần cứng GPU
if not torch.cuda.is_available() or not shutil.which("nvidia-smi"):
    raise RuntimeError(
        "❌ KHÔNG TÌM THẤY GPU!\\n"
        "vLLM bắt buộc phải có GPU để chạy.\\n"
        "👉 Cách sửa trên Kaggle:\\n"
        "   1. Nhìn sang thanh menu bên phải (Session options).\\n"
        "   2. Tại mục 'Accelerator', chọn 'GPU T4 x 2'.\\n"
        "   3. Chờ session khởi động lại rồi chạy lại từ đầu!"
    )

# Model Qwen 3.5 9B Reasoning từ HuggingFace (Mặc định)
# Lưu ý: Qwen/Qwen3.5-9B nặng ~18GB, tải mất 3-5 phút trên Kaggle.
# Bạn cũng có thể dùng 'Qwen/Qwen2.5-Coder-7B-Instruct' nếu muốn nạp siêu nhanh (~14GB).
MODEL_NAME = "Qwen/Qwen3.5-9B"
SERVED_MODEL_NAME = "qwen3.5:9b"

# Phát hiện số GPU khả dụng cho Tensor Parallelism (2x T4 trên Kaggle)
num_gpus = torch.cuda.device_count()
tp_size = 2 if num_gpus >= 2 else 1
print(f"🎮 Số GPU phát hiện: {num_gpus} | Tensor Parallel Size cấu hình: {tp_size}")
if num_gpus < 2:
    print("⚠️ Chú ý: Bạn đang chỉ có 1 GPU. Để chạy mượt mà Qwen 3.5 9B (18GB), hãy chọn 'GPU T4 x 2' trên Kaggle!")

vllm_api_url = "http://127.0.0.1:8000/v1/models"
server_ready = False

try:
    with urllib.request.urlopen(vllm_api_url, timeout=2) as r:
        if r.status == 200:
            server_ready = True
            print("✅ vLLM Server đã chạy sẵn từ trước và sẵn sàng phục vụ!")
except Exception:
    pass

if not server_ready:
    print(f"🚀 Đang khởi động vLLM Server với model {MODEL_NAME} (alias: {SERVED_MODEL_NAME})...")
    print(f"📦 vLLM sẽ tự động tải weights {MODEL_NAME} từ HuggingFace (~18GB) và nạp vào {num_gpus} GPU...")
    print("⏳ Tiến trình có thể mất từ 3 - 6 phút ở lần đầu tiên. Đang theo dõi tiến độ log...")
    
    # 0. Dọn dẹp tiến trình vLLM cũ nếu bị treo từ lần chạy trước
    try:
        subprocess.run(["pkill", "-9", "-f", "vllm"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
    except Exception:
        pass

    # Cấu hình biến môi trường tối ưu cho 2x T4 trên Kaggle
    env = os.environ.copy()
    env["VLLM_USE_V1"] = "0"               # Bắt buộc: Tắt V1 engine để tránh lỗi Engine core crash trên Kaggle
    env["NCCL_P2P_DISABLE"] = "1"          # Bắt buộc: 2x T4 trên Kaggle không có P2P NVLink
    env["VLLM_SKIP_P2P_CHECK"] = "1"        # Bỏ qua kiểm tra P2P để chống treo IPC
    env["NCCL_IB_DISABLE"] = "1"           # Tắt InfiniBand
    env["NCCL_NET_GDR_LEVEL"] = "0"
    env["NCCL_DEBUG"] = "WARN"
    env["TORCH_NCCL_AVOID_RECORD_STREAMS"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    
    vllm_cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", MODEL_NAME,
        "--served-model-name", SERVED_MODEL_NAME,
        "--port", "8000",
        "--tensor-parallel-size", str(tp_size),
        "--gpu-memory-utilization", "0.85",
        "--max-model-len", "4096",
        "--trust-remote-code",
        "--dtype", "float16",              # T4 Compute Capability 7.5 không hỗ trợ bfloat16, bắt buộc dùng float16
        "--enforce-eager",
        "--disable-custom-all-reduce",       # BẮT BUỘC KAGGLE: Chống deadlock shm_broadcast trên dual T4 PCIe
        "--limit-mm-per-prompt", '{"image": 0, "video": 0}',  # Tắt cache ảnh/video vì chỉ suy luận dữ liệu text/SQL
    ]
    
    log_file_path = "vllm_server.log"
    log_f = open(log_file_path, "w", encoding="utf-8")
    p = subprocess.Popen(vllm_cmd, env=env, stdout=log_f, stderr=log_f)
    
    start_time = time.time()
    max_wait_seconds = 600  # 10 phút tối đa để tải 18GB
    last_reported = 0
    
    while time.time() - start_time < max_wait_seconds:
        time.sleep(3)
        elapsed = int(time.time() - start_time)
        
        # 1. Phát hiện crash sớm: nếu process đã thoát, dừng ngay và in log lỗi
        exit_code = p.poll()
        if exit_code is not None:
            log_f.close()
            with open(log_file_path, "r", encoding="utf-8", errors="replace") as rf:
                err_logs = rf.read()
            raise RuntimeError(
                f"❌ vLLM Server bị dừng đột ngột (Exit code: {exit_code})!\\n"
                f"--- CHI TIẾT LỖI TỪ vllm_server.log ---\\n{err_logs}"
            )
        
        # 2. Kiểm tra endpoint đã phản hồi 200 OK chưa
        try:
            with urllib.request.urlopen(vllm_api_url, timeout=2) as r:
                if r.status == 200:
                    server_ready = True
                    print(f"\\n🎉 THÀNH CÔNG: vLLM Server Qwen 3.5 9B đã sẵn sàng tại http://127.0.0.1:8000/v1 (sau {elapsed}s)!")
                    break
        except Exception:
            pass
        
        # 3. Đọc dòng log mới nhất để báo tiến độ tải file
        if elapsed - last_reported >= 15:
            last_reported = elapsed
            try:
                with open(log_file_path, "r", encoding="utf-8", errors="replace") as rf:
                    lines = [l.strip() for l in rf.readlines() if l.strip()]
                    last_line = lines[-1] if lines else "Đang khởi tạo..."
                    print(f"   [{elapsed}s] {last_line[:120]}")
            except Exception:
                print(f"   [{elapsed}s] Đang tải mô hình...")

if not server_ready:
    with open(log_file_path, "r", encoding="utf-8", errors="replace") as rf:
        err_logs = rf.read()
    raise RuntimeError(
        f"❌ vLLM Server không phản hồi sau {max_wait_seconds}s!\\n"
        f"--- CHI TIẾT LOG ---\\n{err_logs}"
    )

# 4. Gửi test request kiểm tra phản hồi
import requests
res = requests.post(
    "http://127.0.0.1:8000/v1/chat/completions",
    json={
        "model": SERVED_MODEL_NAME,
        "messages": [{"role": "user", "content": "print('Qwen 3.5 9B is ready')"}],
        "max_tokens": 30
    },
    timeout=30
)
print("💬 Phản hồi test từ vLLM:", res.json()["choices"][0]["message"]["content"])""")
  )

  # Cell 6: Unit Tests
  nb['cells'].append(
      md("""## 5. Chạy Toàn Bộ Unit Tests
Đảm bảo toàn bộ 38 bài kiểm thử nghiệp vụ, calendar, sandbox, data ingestion, và abstain gate đều PASS 100%.""")
  )
  nb['cells'].append(
      code("""!pytest tests/ -q""")
  )

  # Cell 7: Single Question Smoke Test
  nb['cells'].append(
      md("""## 6. Thử Nghiệm Câu Hỏi Mẫu Đơn Lẻ (Smoke Test)
Kiểm tra nhanh 1 câu hỏi từ tập `public_test` kết nối trực tiếp với vLLM endpoint.""")
  )
  nb['cells'].append(
      code("""from pathlib import Path
import json
from src.agent_pipeline import ReasoningPipeline
from src.llm_client import OpenAICompatibleClient
from IPython.display import display, Markdown

# Khởi tạo Pipeline kết nối với vLLM API
llm = OpenAICompatibleClient(
    model_name=SERVED_MODEL_NAME,
    base_url="http://127.0.0.1:8000/v1",
    timeout=90.0
)
pipeline = ReasoningPipeline(
    rulebook_path=Path("public_test/rulebook.md"),
    calendar_path=Path("public_test/calendar.csv"),
    llm_client=llm,
    sandbox_timeout=10.0,
    max_retries=2,
    enable_reasoning=True
)

# Đọc câu hỏi đầu tiên của tập public_test
with open("public_test/questions.jsonl", "r", encoding="utf-8") as f:
    sample_q = json.loads(f.readline())

biz_dir = Path("public_test/data") / sample_q["business_id"]
print(f"📌 Câu hỏi ID: {sample_q['id']} | Shop: {sample_q['business_id']}")
print(f"💬 Nội dung: {sample_q['question']}")
print(f"📅 As of date: {sample_q.get('as_of_date')}")
print("-" * 60)

demo_ans = pipeline.solve_question(sample_q, biz_dir, log_dir=Path("result/single_demo"))

with open(f"result/single_demo/{sample_q['id']}.json", "r", encoding="utf-8") as f:
    demo_log = json.load(f)

trace = demo_log.get("trace", [{}])[-1]
reasoning_text = trace.get("reasoning") or trace.get("raw_response") or "N/A"
code_text = trace.get("code") or "# N/A"

display(Markdown(f\"\"\"### 💭 BƯỚC SUY LUẬN (REASONING):
```text
{reasoning_text}
```

### 💻 MÃ NGUỒN PYTHON DUCKDB:
```python
{code_text}
```

### ⚡ ĐÁP ÁN:
- **Type:** `{demo_ans.get('type')}`
- **Answer:** `{demo_ans.get('answer', demo_ans.get('reason'))}`
- **Thời gian chạy:** `{demo_log.get('elapsed_seconds')}s`
\"\"\"))""")
  )

  # Cell 8: MAIN RUNNER - 1,000 Questions with vLLM & 4 Workers
  nb['cells'].append(
      md("""## 7. 🚀 CHẠY SUY LUẬN 1,000 CÂU PUBLIC TEST BẰNG vLLM (4 WORKERS)
- Chạy song song **4 workers** tận dụng tối đa Continuous Batching của vLLM.
- Tự động nạp sẵn **DuckDB in-memory cache** cho toàn bộ 14 shop.
- Ghi đĩa / Google Drive tức thì sau từng câu hỏi.
- **Tự động kích hoạt chế độ `--resume`**: Nếu bị ngắt kết nối giữa chừng, chỉ cần chạy lại cell này là hệ thống tiếp tục làm câu tiếp theo!""")
  )
  nb['cells'].append(
      code("""import os
from pathlib import Path

SUBMISSION_FILE = os.path.join(OUTPUT_DIR, "submission.jsonl")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

print("=" * 60)
print("🚀 BẮT ĐẦU CHẠY SUY LUẬN 1,000 CÂU PUBLIC TEST VỚI vLLM (QWEN 3.5 9B)")
print(f"- Output Submission: {SUBMISSION_FILE}")
print(f"- Logs Directory   : {LOGS_DIR}")
print(f"- Backend / Model  : vllm ({MODEL_NAME} -> {SERVED_MODEL_NAME})")
print(f"- Workers          : 4 luồng song song (vLLM PagedAttention Batching)")
print(f"- Resume Mode      : BẬT")
print("=" * 60)

# Thực thi lệnh dự đoán bằng vLLM backend
!python predict.py \\
  --input-dir public_test \\
  --output {SUBMISSION_FILE} \\
  --log-dir {LOGS_DIR} \\
  --model-backend vllm \\
  --model-name {SERVED_MODEL_NAME} \\
  --api-url http://127.0.0.1:8000/v1 \\
  --workers 4 \\
  --resume""")
  )

  # Cell 9: Validate Submission Format
  nb['cells'].append(
      md("""## 8. ✅ Kiểm Tra Tính Toàn Vẹn File Kết Quả (Submission Validator)
Quét toàn bộ file `submission.jsonl` để đảm bảo:
- Đủ 1,000 câu hỏi, không câu nào bị sót hay trùng lặp.
- 100% đúng cú pháp JSON per line.
- Đúng 9 kiểu định dạng: number, percent, string, date, boolean, list, table, unanswerable, abstain.""")
  )
  nb['cells'].append(
      code("""!python scripts/validate_submission.py {SUBMISSION_FILE} --questions public_test/questions.jsonl""")
  )

  # Cell 10: Log Inspector & Merge Logs
  nb['cells'].append(
      md("""## 9. 🔍 Gộp Toàn Bộ Log Thành 1 File & Phân Tích Kết Quả
Gộp tất cả file JSON riêng lẻ trong thư mục logs thành `all_logs.json`, `merged_logs.jsonl` và thống kê phân bố đáp án.""")
  )
  nb['cells'].append(
      code("""import json, glob, zipfile, os
from pathlib import Path
import pandas as pd
from IPython.display import display, Markdown

# 1. Tìm tất cả file log
log_files = sorted(glob.glob(f"{LOGS_DIR}/*.json"))
if not log_files:
    log_files = sorted(glob.glob("result/logs/*.json"))
print(f"📦 Tìm thấy {len(log_files)} file log.")

# 2. Gộp thành 1 file JSON duy nhất (all_logs.json)
all_logs = []
rows = []
for lf in log_files:
    try:
        with open(lf, "r", encoding="utf-8") as f:
            d = json.load(f)
            all_logs.append(d)
            
            ans = d.get("answer") or d.get("final_answer", {})
            rows.append({
                "id": d.get("id"),
                "type": ans.get("type"),
                "answer": str(ans.get("answer", ans.get("reason"))),
                "elapsed_s": round(d.get("elapsed_ms", 0) / 1000.0, 2) if "elapsed_ms" in d else d.get("elapsed_seconds", 0),
                "has_code": bool(d.get("code")),
                "has_thinking": bool(d.get("thinking"))
            })
    except Exception as e:
        pass

merged_json_path = os.path.join(OUTPUT_DIR, "all_logs.json")
with open(merged_json_path, "w", encoding="utf-8") as f:
    json.dump(all_logs, f, ensure_ascii=False, indent=2)
print(f"✅ Đã gộp thành công vào: {merged_json_path}")

# 3. Gộp thành file JSONL
merged_jsonl_path = os.path.join(OUTPUT_DIR, "merged_logs.jsonl")
with open(merged_jsonl_path, "w", encoding="utf-8") as f:
    for item in all_logs:
        f.write(json.dumps(item, ensure_ascii=False) + "\\n")
print(f"✅ Đã tạo file JSONL: {merged_jsonl_path}")

# 4. Hiển thị bảng tổng hợp
if rows:
    df_summary = pd.DataFrame(rows)
    print("\\n" + "=" * 60)
    print("📊 BÁO CÁO TIẾN ĐỘ & PHÂN BỐ ĐÁP ÁN (vLLM RUN):")
    print(f"- Tổng số câu đã ghi nhận: {len(df_summary)}")
    print(f"- Thời gian trung bình: {df_summary['elapsed_s'].mean():.2f} giây/câu")
    print(f"- Số câu có code: {df_summary['has_code'].sum()} | Có reasoning: {df_summary['has_thinking'].sum()}")
    print("\\nPhân bố loại đáp án:")
    print(df_summary['type'].value_counts())
    print("=" * 60)
    display(df_summary.head(10))

# 5. Đóng gói file ZIP để tải về máy
zip_path = os.path.join(OUTPUT_DIR, "vllm_logs_and_submission.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    if os.path.exists(SUBMISSION_FILE):
        zipf.write(SUBMISSION_FILE, arcname="submission.jsonl")
    zipf.write(merged_json_path, arcname="all_logs.json")
    zipf.write(merged_jsonl_path, arcname="merged_logs.jsonl")
    for lf in log_files[:100]:
        zipf.write(lf, arcname=f"sample_logs/{Path(lf).name}")
print(f"\\n✅ Đã đóng gói ZIP: {zip_path} ({os.path.getsize(zip_path)/1024:.1f} KB)")""")
  )

  # Cell 11: Download Submission & Logs
  nb['cells'].append(
      md("""## 10. ⬇️ Tải File `submission.jsonl` và Log Về Máy Tính
Tải file kết quả về máy tính để nộp lên cổng cuộc thi Zalo AI Challenge.""")
  )
  nb['cells'].append(
      code("""if ENV == "colab":
    from google.colab import files
    print("⬇️ Đang mở hộp thoại tải file submission.jsonl...")
    if os.path.exists(SUBMISSION_FILE):
        files.download(SUBMISSION_FILE)
    print("⬇️ Đang mở hộp thoại tải file all_logs.json...")
    if os.path.exists(merged_json_path):
        files.download(merged_json_path)
elif ENV == "kaggle":
    from IPython.display import FileLink, display
    print("📁 Các file đã sẵn sàng trong Output! Click link bên dưới để tải trực tiếp:")
    if os.path.exists(SUBMISSION_FILE):
        display(FileLink(SUBMISSION_FILE))
    display(FileLink(zip_path))
else:
    print(f"📁 Chạy trên môi trường local, file kết quả ở tại: {SUBMISSION_FILE}")""")
  )

  return nb


def main():
  nb = build_vllm_notebook()
  p = Path('notebooks/qwen35_vllm_reasoning_benchmark.ipynb')
  p.parent.mkdir(parents=True, exist_ok=True)
  with open(p, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
  print(f'✅ Đã tạo thành công: {p} ({len(nb["cells"])} cells)')


if __name__ == '__main__':
  main()
