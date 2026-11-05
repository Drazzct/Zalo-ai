"""Prompt Generator Module for Zalo AI DataMate.

Assembles comprehensive, highly structured prompts for LLMs (Qwen2.5-Coder /
CodeLlama)
to generate executable DuckDB / Python analytical scripts for Vietnamese SME
questions.
"""

from typing import Any, Dict, List, Optional


class PromptGenerator:
  """Constructs zero-shot / few-shot prompts with schema, rules, temporal context, and error reflection."""

  SYSTEM_PROMPT = """Bạn là Chuyên gia Phân tích Dữ liệu cấp cao và Kỹ sư SQL/Python cho hệ thống DataMate (Zalo AI).
Nhiệm vụ của bạn là viết một hàm Python `solve(con)` nhận kết nối DuckDB `con` để tính toán chính xác câu trả lời cho câu hỏi nghiệp vụ kinh doanh của cửa hàng.

QUY TẮC BẮT BUỘC:
1. ĐÚNG CHUẨN KINH DOANH (Rulebook):
   - Doanh thu: Chỉ tính các đơn không huỷ và không trả hàng (đơn có trả một phần cũng bỏ cả đơn). Bằng tổng thành tiền các dòng (đã trừ giảm giá dòng, không trừ voucher đơn, không gồm VAT/ship).
   - Tỉ lệ huỷ đơn: Bằng (số đơn bị huỷ / TỔNG MỌI ĐƠN ĐẶT TRONG KỲ bao gồm cả huỷ, trả, đang giao) * 100, làm tròn 2 chữ số thập phân.
   - Bán chạy nhất: Xếp theo số lượng quy về đơn vị cơ bản (bỏ đơn huỷ, trả).
   - Bằng nhau: Nếu bằng nhau ở tiêu chí câu hỏi, xếp theo mã tăng dần (hoặc tên tăng dần nếu không có mã).
   - Kỳ ngoài khoảng dữ liệu: Nếu kỳ hỏi nằm HOÀN TOÀN ngoài khoảng ngày có dữ liệu của shop, trả về {"type": "unanswerable", "reason": "Dữ liệu không có kỳ này"}.
   - Tên bảng và cột: BẮT BUỘC chỉ truy vấn tên bảng và cột THỰC TẾ có trong phần "CƠ SỞ DỮ LIỆU CỬA HÀNG" bên dưới. TUYỆT ĐỐI KHÔNG copy tên bảng từ ví dụ minh họa nếu shop không có bảng đó!
2. ĐỊNH DẠNG ĐÁP ÁN:
   - type = "number": Số thực hoặc số nguyên (tiền là số nguyên VND, làm tròn về đồng). KHÔNG kèm chữ 'đ' hay dấu phẩy.
   - type = "percent": Số phần trăm làm tròn 2 chữ số thập phân (ví dụ: 12.45, -5.20). KHÔNG kèm ký hiệu %.
   - type = "date": "YYYY-MM-DD" hoặc "YYYY-MM".
   - type = "boolean": true hoặc false.
   - type = "string": Tên như trong dữ liệu hoặc mã hàng.
   - type = "list": Mảng JSON có thứ tự [val1, val2, ...].
   - type = "table": {"columns": ["col1", "col2"], "rows": [[val1, val2], ...]}.
   - type = "unanswerable": {"type": "unanswerable", "reason": "..."}.
3. MÃ NGUỒN:
   - Chỉ trả về duy nhất khối mã Python trong thẻ ```python ... ```.
   - Hàm `solve(con)` phải trả về một dictionary: `{"type": ..., "answer": ...}` (hoặc `{"type": "unanswerable", "reason": ...}`).
"""

  FEW_SHOT_EXAMPLES = """
### VÍ DỤ MẪU (LƯU Ý: Đổi tên bảng và tên cột theo đúng danh sách bảng của shop ở trên, KHÔNG copy y nguyên don_hang_chi_tiet nếu shop không có):

Ví dụ 1: "Tổng doanh thu trong ngày hôm nay là bao nhiêu?" (as_of_date: 2025-04-30)
```python
def solve(con):
    # Đơn doanh thu: không huỷ, không trả
    query = \"\"\"
    SELECT COALESCE(SUM(thanh_tien), 0)
    FROM don_hang_chi_tiet
    WHERE ngay_dat_hang = '2025-04-30'
      AND LOWER(trang_thai_don_hang) NOT LIKE '%hu%'
      AND LOWER(trang_thai_don_hang) NOT LIKE '%tr%'
    \"\"\"
    res = con.execute(query).fetchone()[0]
    return {
        "type": "number",
        "answer": int(round(res))
    }
```

Ví dụ 2: "Tỉ lệ huỷ đơn tháng 6/2025 là bao nhiêu %?" (as_of_date: 2026-06-24)
```python
def solve(con):
    query = \"\"\"
    SELECT 
        COUNT(DISTINCT ma_don_hang) AS total_orders,
        COUNT(DISTINCT CASE WHEN LOWER(trang_thai_don_hang) LIKE '%hu%' THEN ma_don_hang END) AS cancelled_orders
    FROM don_hang_chi_tiet
    WHERE ngay_dat_hang >= '2025-06-01' AND ngay_dat_hang <= '2025-06-30'
    \"\"\"
    row = con.execute(query).fetchone()
    total, cancelled = row[0], row[1]
    if total == 0:
        return {"type": "unanswerable", "reason": "Không có đơn hàng nào trong tháng 6/2025"}
    rate = round((cancelled / total) * 100, 2)
    return {
        "type": "percent",
        "answer": rate
    }
```
"""

  @classmethod
  def get_few_shot_examples(cls, available_tables: Optional[List[str]] = None) -> str:
    tbl = 'don_hang_chi_tiet'
    if available_tables:
      for candidate in available_tables:
        c_low = candidate.lower()
        if any(w in c_low for w in ['ban_hang', 'hoa_don', 'don_hang', 'ban']):
          tbl = candidate
          break
      else:
        tbl = available_tables[0]

    return f"""### VÍ DỤ MẪU (LƯU Ý: Đổi tên bảng và cột theo đúng danh sách bảng của shop ở trên):

Ví dụ 1: "Tổng doanh thu trong ngày hôm nay là bao nhiêu?" (as_of_date: 2025-04-30)
```python
def solve(con):
    # Đơn doanh thu: không huỷ, không trả
    query = \"\"\"
    SELECT COALESCE(SUM(thanh_tien), 0)
    FROM {tbl}
    WHERE ngay_dat_hang = '2025-04-30'
      AND LOWER(trang_thai) NOT LIKE '%hu%'
      AND LOWER(trang_thai) NOT LIKE '%tr%'
    \"\"\"
    res = con.execute(query).fetchone()[0]
    return {{
        "type": "number",
        "answer": int(round(res))
    }}
```

Ví dụ 2: "Tỉ lệ huỷ đơn tháng 6/2025 là bao nhiêu %?" (as_of_date: 2026-06-24)
```python
def solve(con):
    query = \"\"\"
    SELECT 
        COUNT(DISTINCT ma_don_hang) AS total_orders,
        COUNT(DISTINCT CASE WHEN LOWER(trang_thai) LIKE '%hu%' THEN ma_don_hang END) AS cancelled_orders
    FROM {tbl}
    WHERE ngay_dat_hang >= '2025-06-01' AND ngay_dat_hang <= '2025-06-30'
    \"\"\"
    row = con.execute(query).fetchone()
    total, cancelled = row[0], row[1]
    if total == 0:
        return {{"type": "unanswerable", "reason": "Không có đơn hàng nào trong tháng 6/2025"}}
    rate = round((cancelled / total) * 100, 2)
    return {{
        "type": "percent",
        "answer": rate
    }}
```
"""

  @classmethod
  def generate_prompt(
      cls,
      question: str,
      as_of_date: str,
      schema_context: str,
      rules_summary: str,
      temporal_anchors: Dict[str, Any],
      available_tables: Optional[List[str]] = None
  ) -> str:
    """Generate master prompt combining schema, rules, temporal anchors, and user question."""
    temp_info = []
    if temporal_anchors.get('primary_window'):
      s, e = temporal_anchors['primary_window']
      temp_info.append(f'- Khoảng thời gian chính: từ {s} đến {e}')
    if temporal_anchors.get('compare_window'):
      cs, ce = temporal_anchors['compare_window']
      temp_info.append(f'- Khoảng thời gian so sánh (kỳ trước): từ {cs} đến {ce}')
    if temporal_anchors.get('detected_phrases'):
      phrases = ', '.join(temporal_anchors['detected_phrases'])
      temp_info.append(f'- Cụm từ thời gian nhận diện: {phrases}')

    temp_context_str = '\n'.join(temp_info) if temp_info else '- Không xác định được cụm từ thời gian đặc biệt.'
    few_shots = cls.get_few_shot_examples(available_tables)

    prompt = f"""{cls.SYSTEM_PROMPT}

{schema_context}

{rules_summary}

{few_shots}

### THÔNG TIN THỜI GIAN ĐÃ XÁC ĐỊNH:
- Ngày mốc (as_of_date): {as_of_date}
{temp_context_str}

### CÂU HỎI CỦA NGƯỜI DÙNG:
\"{question}\" (as_of_date: {as_of_date})

Hãy viết hàm `solve(con)` bằng Python để trả lời câu hỏi trên:
"""
    return prompt

  @classmethod
  def generate_reflection_prompt(
      cls,
      original_prompt: str,
      previous_code: str,
      error_message: str
  ) -> str:
    """Generate self-reflection prompt providing the error feedback to the LLM."""
    hint = ""
    if "does not exist" in error_message.lower():
      hint = "\nLƯU Ý ĐẶC BIỆT: Bảng hoặc cột trên không tồn tại trong database của shop! Vui lòng đọc kỹ danh sách bảng và cột thực tế trong phần CƠ SỞ DỮ LIỆU CỬA HÀNG ở trên để dùng đúng bảng có thật.\n"

    reflection = f"""{original_prompt}

### MÃ BẠN ĐÃ VIẾT TRƯỚC ĐÓ:
```python
{previous_code}
```

### THÔNG BÁO LỖI KHI THỰC THI (SANDBOX ERROR):
{error_message}
{hint}
Hãy phân tích lỗi trên (ví dụ: sai tên cột/bảng, chia cho 0, query trả về rỗng, sai kiểu dữ liệu), viết lại hàm `solve(con)` hoàn chỉnh và sửa triệt để lỗi:
"""
    return reflection

