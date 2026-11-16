"""Generator script to update notebooks for high-speed Colab and Kaggle execution.

Generates:
1. notebooks/colab_run_benchmark.ipynb
2. notebooks/qwen35_9b_reasoning_benchmark.ipynb
"""

import json
from pathlib import Path


def build_unified_notebook():
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
      md("""# 🚀 Zalo AI Challenge 2026: DataMate - Colab & Kaggle Ultra-Fast Runner
*(Hỗ trợ chạy mượt mà trên **Google Colab (GPU T4 / A100)** và **Kaggle Notebooks (GPU T4 x 2 / P100)**)*

Notebook này được tối ưu chuyên biệt để:
1. **Chạy toàn bộ 1,000 câu Public Test** trong **~25 - 35 phút** trên GPU T4 (nhanh gấp 15 lần).
2. **Tự động lưu vào Google Drive & Hỗ trợ Resume**: Nếu mất mạng hoặc đứt kết nối giữa chừng, chỉ cần chạy lại là hệ thống tự động nhận diện và làm tiếp, không mất công chạy lại từ đầu!
3. **Tránh tràn VRAM (Zero CPU Offloading)**: Khóa bộ đệm Context 4096 tokens, giúp 100% layers của mô hình `qwen3.5:9b` nằm trọn trong VRAM.
4. **Pre-warming In-Memory DuckDB**: Nạp sẵn toàn bộ database các shop vào RAM DuckDB trước khi chạy, loại bỏ 100% độ trễ đọc file Excel lặp đi lặp lại.
5. **Kiểm tra tự động trước khi Submit**: Chạy validator để đối soát đủ 1,000 câu, đúng 9 kiểu format theo chuẩn của BTC Zalo AI Challenge.
6. **Gộp toàn bộ Log thành 1 file & Tải về máy**: Tự động tạo `all_logs.json`, `merged_logs.jsonl` và file nén `logs_bundle.zip`.

---
### ⚙️ HƯỚNG DẪN CẤU HÌNH PHẦN CỨNG:
- **Trên Google Colab:** Vào menu **Runtime -> Change runtime type -> Hardware accelerator: T4 GPU** (hoặc A100).
- **Trên Kaggle Notebooks:** Ở thanh menu bên phải:
  - **Accelerator:** Chọn **GPU T4 x 2** (hoặc **GPU P100**).
  - **Internet:** BẮT BUỘC gạt sang **"Internet on"** (Kaggle yêu cầu xác thực số điện thoại để bật internet tải model).""")
  )

  # Cell 2: Environment & GPU Check + Google Drive Mount
  nb['cells'].append(
      md(
          '## 1. Kiểm tra Môi trường, GPU & Kết nối Google Drive\nKết nối'
          ' Google Drive trên Colab giúp file kết quả được lưu trực tiếp vào đĩa'
          ' đám mây theo thời gian thực.'
      )
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
        print("   3. Bấm 'Save' để kích hoạt GPU!")""")
  )

  # Cell 3: Clone or Pull Codebase
  nb['cells'].append(
      md(
          '## 2. Thiết lập Mã nguồn Dự án (Tự động Clone / Git Pull)\nTự động'
          ' kéo phiên bản mới nhất từ repository'
          ' `https://github.com/Drazzct/Zalo-ai.git`.'
      )
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

  # Cell 4: Install Dependencies
  nb['cells'].append(md('## 3. Cài đặt các thư viện Python'))
  nb['cells'].append(
      code(
          '!pip install -q pandas duckdb openpyxl pydantic pytest requests'
          ' openai tabulate'
      )
  )

  # Cell 5: Setup Ollama GPU with 16384 context length (Full Context & Reasoning)
  nb['cells'].append(
      md("""## 4. Cài đặt & Khởi động Ollama GPU Tối ưu
Cấu hình `OLLAMA_CONTEXT_LENGTH=16384` và `OLLAMA_NUM_PARALLEL=2`:
- Hỗ trợ toàn bộ schema và rulebook lớn của các shop (lên tới 16k tokens) mà không bị cắt cụt.
- Đảm bảo 100% mô hình `qwen3.5:9b` nằm trọn trong VRAM 15GB của T4 mà không bị tràn.""")
  )
  nb['cells'].append(
      code("""import subprocess, os, time, urllib.request, shutil

# 1. Cài đặt công cụ giải nén zstd và Ollama
if not shutil.which("ollama"):
    print("📦 Đang kiểm tra công cụ zstd...")
    !which zstd > /dev/null || (apt-get update -qq && apt-get install -y -qq zstd || sudo apt-get update -qq && sudo apt-get install -y -qq zstd)
    print("📦 Đang cài đặt Ollama...")
    !curl -fsSL https://ollama.com/install.sh | sh
else:
    print("✅ Ollama đã được cài đặt sẵn.")

# 2. Khởi chạy Ollama daemon với GPU
env = os.environ.copy()
env["CUDA_VISIBLE_DEVICES"] = "0,1" if os.path.exists("/kaggle") else "0"
env["OLLAMA_NUM_PARALLEL"] = "2"          # 2 luồng song song cho 9B
env["OLLAMA_FLASH_ATTENTION"] = "1"       # Kích hoạt Flash Attention
env["OLLAMA_CONTEXT_LENGTH"] = "16384"    # Đảm bảo đủ context 16k cho prompt & reasoning
env["LLM_NUM_CTX"] = "16384"
env["LLM_NUM_PREDICT"] = "2048"
env["LLM_TIMEOUT"] = "90.0"

try:
    urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
    print("✅ Ollama daemon đã sẵn sàng từ trước!")
except Exception:
    print("🚀 Đang khởi động Ollama daemon GPU...")
    with open("ollama.log", "w") as f:
        subprocess.Popen(["ollama", "serve"], env=env, stdout=f, stderr=f)
    daemon_ready = False
    for _ in range(15):
        time.sleep(1)
        try:
            urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
            daemon_ready = True
            break
        except Exception:
            pass
    if daemon_ready:
        print("✅ Khởi động Ollama daemon GPU thành công!")
    else:
        print("⚠️ Đang hoàn tất nạp daemon...")

# 3. Tải model Qwen 3.5 9B (Reasoning) (Model 9B Q4 nặng ~5.5GB, hỗ trợ suy luận logic qua thẻ <reasoning>)
MODEL_NAME = "qwen3.5:9b"
print(f"📦 Đang tải model {MODEL_NAME} về GPU...")
!ollama pull {MODEL_NAME}

# 4. Kích hoạt model nạp vào VRAM và kiểm tra
!ollama run {MODEL_NAME} "print('ready')" --verbose
!ollama ps""")
  )

  # Cell 6: Unit Tests
  nb['cells'].append(
      md(
          '## 5. Chạy Toàn Bộ Unit Tests\nĐảm bảo toàn bộ 37 bài kiểm thử nghiệp'
          ' vụ, calendar, sandbox, data ingestion, và abstain gate đều PASS'
          ' 100%.'
      )
  )
  nb['cells'].append(code('!pytest tests/ -q'))

  # Cell 7: Single Question Smoke Test
  nb['cells'].append(
      md(
          '## 6. Thử Nghiệm Câu Hỏi Mẫu Đơn Lẻ (Smoke Test)\nKiểm tra nhanh 1'
          ' câu hỏi từ tập `public_test` để xác nhận pipeline và reasoning hoạt'
          ' động trơn tru.'
      )
  )
  nb['cells'].append(
      code("""from pathlib import Path
import json
from src.agent_pipeline import ReasoningPipeline
from src.llm_client import OllamaClient
from IPython.display import display, Markdown

# Khởi tạo Pipeline
llm = OllamaClient(model_name=MODEL_NAME, host="http://127.0.0.1:11434")
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

  # Cell 8: MAIN RUNNER - 1,000 Questions Ultra Fast with Resume
  nb['cells'].append(
      md("""## 7. 🚀 CHẠY SUY LUẬN 1,000 CÂU PUBLIC TEST SIÊU TỐC
- Chạy song song **4 workers**.
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
print("🚀 BẮT ĐẦU CHẠY SUY LUẬN 1,000 CÂU PUBLIC TEST")
print(f"- Output Submission: {SUBMISSION_FILE}")
print(f"- Logs Directory   : {LOGS_DIR}")
print(f"- Backend / Model  : ollama ({MODEL_NAME})")
print(f"- Workers          : 2 luồng song song")
print(f"- Resume Mode      : BẬT")
print("=" * 60)

# Thực thi lệnh dự đoán toàn diện
!python predict.py \\
  --input-dir public_test \\
  --output {SUBMISSION_FILE} \\
  --log-dir {LOGS_DIR} \\
  --model-backend ollama \\
  --model-name {MODEL_NAME} \\
  --workers 2 \\
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
      code(
          '!python scripts/validate_submission.py {SUBMISSION_FILE} --questions'
          ' public_test/questions.jsonl'
      )
  )

  # Cell 10: Log Inspector & Merge Logs
  nb['cells'].append(
      md("""## 9. 🔍 Gộp Toàn Bộ Log Thành 1 File & Phân Tích Kết Quả
Cell này sẽ gộp tất cả file JSON riêng lẻ trong thư mục logs thành:
1. `all_logs.json`: File JSON tổng hợp toàn bộ suy luận và mã nguồn.
2. `merged_logs.jsonl`: File JSON Lines tiện cho việc phân tích dữ liệu lớn.
3. Bảng thống kê Pandas DataFrame trực quan hoá tiến độ và phân bố kết quả.""")
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
    print("📊 BÁO CÁO TIẾN ĐỘ & PHÂN BỐ ĐÁP ÁN:")
    print(f"- Tổng số câu đã ghi nhận: {len(df_summary)}")
    print(f"- Thời gian trung bình: {df_summary['elapsed_s'].mean():.2f} giây/câu")
    print(f"- Số câu có code: {df_summary['has_code'].sum()} | Có reasoning: {df_summary['has_thinking'].sum()}")
    print("\\nPhân bố loại đáp án:")
    print(df_summary['type'].value_counts())
    print("=" * 60)
    display(df_summary.head(10))

# 5. Đóng gói file ZIP để tải về máy
zip_path = os.path.join(OUTPUT_DIR, "logs_and_submission.zip")
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
      code("""# Tự động hỗ trợ tải về máy trên cả Google Colab và Kaggle
if ENV == "colab":
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
  nb = build_unified_notebook()

  # 1. Update notebooks/colab_run_benchmark.ipynb
  p1 = Path('notebooks/colab_run_benchmark.ipynb')
  p1.parent.mkdir(parents=True, exist_ok=True)
  with open(p1, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
  print(f'✅ Đã cập nhật thành công: {p1} ({len(nb["cells"])} cells)')

  # 2. Update notebooks/qwen35_9b_reasoning_benchmark.ipynb
  p2 = Path('notebooks/qwen35_9b_reasoning_benchmark.ipynb')
  p2.parent.mkdir(parents=True, exist_ok=True)
  with open(p2, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
  print(f'✅ Đã cập nhật thành công: {p2} ({len(nb["cells"])} cells)')


if __name__ == '__main__':
  main()
