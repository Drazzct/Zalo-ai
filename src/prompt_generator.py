"""Prompt Generator Module for Zalo AI DataMate.

Assembles comprehensive, highly structured prompts for LLMs (Qwen2.5-Coder / CodeLlama)
to generate executable DuckDB / Python analytical scripts for Vietnamese SME questions.
"""

from typing import Any, Dict, List, Optional


class PromptGenerator:
  """Constructs zero-shot / few-shot prompts with schema, rules, temporal context, table routing, and error reflection."""

  SYSTEM_PROMPT = """Bạn là Chuyên gia Phân tích Dữ liệu cấp cao và Kỹ sư SQL/Python cho hệ thống DataMate (Zalo AI).
Nhiệm vụ của bạn là viết một hàm Python `solve(con)` nhận kết nối DuckDB `con` để tính toán chính xác câu trả lời cho câu hỏi nghiệp vụ kinh doanh của cửa hàng.

QUY TẮC BẮT BUỘC:
1. ĐÚNG CHUẨN KINH DOANH (Rulebook):
   - Doanh thu: Chỉ tính các đơn không huỷ và không trả hàng (đơn có trả một phần cũng bỏ cả đơn). Bằng tổng thành tiền các dòng (đã trừ giảm giá dòng, không trừ voucher đơn, không gồm VAT/ship).
   - Tỉ lệ huỷ đơn: Bằng (số đơn bị huỷ / TỔNG MỌI ĐƠN ĐẶT TRONG KỲ bao gồm cả huỷ, trả, đang giao) * 100, làm tròn 2 chữ số thập phân.
   - Bán chạy nhất: Xếp theo số lượng quy về đơn vị cơ bản (bỏ đơn huỷ, trả).
   - Bằng nhau: Nếu bằng nhau ở tiêu chí câu hỏi, xếp theo mã tăng dần (hoặc tên tăng dần nếu không có mã).
   - Kỳ ngoài khoảng dữ liệu: Nếu kỳ hỏi nằm HOÀN TOÀN ngoài khoảng ngày có dữ liệu của shop, trả về {"type": "unanswerable", "reason": "Dữ liệu không có kỳ này"}.
   - Tên bảng và cột: BẮT BUỘC chỉ truy vấn tên bảng và cột THỰC TẾ có trong phần "CƠ SỞ DỮ LIỆU CỬA HÀNG" bên dưới. TUYỆT ĐỐI KHÔNG bịa tên bảng hoặc cột không tồn tại!
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
4. QUY TẮC SQL CHUẨN XÁC CHO SME (RẤT QUAN TRỌNG):
   - Xử lý Tiếng Việt có dấu trong SQL: Từ "hủy" chứa ký tự "ủ" KHÔNG khớp với "u" trong LIKE '%hu%'!
     Khi lọc đơn hủy, BẮT BUỘC kiểm tra cả dấu và không dấu:
     `(LOWER(col) LIKE '%hu%' OR LOWER(col) LIKE '%hủy%' OR LOWER(col) LIKE '%huỷ%' OR LOWER(col) LIKE '%cancel%')`
     Khi loại trừ hủy và trả:
     `(LOWER(col) NOT LIKE '%hu%' AND LOWER(col) NOT LIKE '%hủy%' AND LOWER(col) NOT LIKE '%cancel%' AND LOWER(col) NOT LIKE '%tr%' AND LOWER(col) NOT LIKE '%trả%')`
   - So sánh Thời gian/Ngày: Cột ngày trong database có thể là VARCHAR hoặc TIMESTAMP chứa cả giờ phút ('YYYY-MM-DD HH:MM:SS').
     Khi so sánh hoặc lọc theo ngày, BẮT BUỘC dùng:
     `SUBSTRING(CAST(col AS VARCHAR), 1, 10) = 'YYYY-MM-DD'`
     hoặc trong khoảng ngày:
     `SUBSTRING(CAST(col AS VARCHAR), 1, 10) >= 'YYYY-MM-DD' AND SUBSTRING(CAST(col AS VARCHAR), 1, 10) <= 'YYYY-MM-DD'`
     TUYỆT ĐỐI KHÔNG dùng so sánh bằng trực tiếp `col = 'YYYY-MM-DD'` nếu cột chứa giờ phút.
   - Bảng chia theo thời gian hoặc nghiệp vụ: Nếu shop có nhiều bảng (ví dụ bảng năm 2025 và bảng năm 2026, hoặc bảng bán hàng vs bảng nhập hàng), hãy đọc kỹ phần "GỢI Ý BẢNG VÀ CỘT PHÙ HỢP" và khoảng ngày (Kỳ) của từng bảng để chọn đúng bảng.
"""

  @classmethod
  def detect_table_columns(
      cls, tbl: str, table_profiles: Optional[Dict[str, Any]]
  ) -> Dict[str, str]:
    """Detect primary date, money, status, and order_id columns for a table."""
    cols_info = {
        'tbl': tbl,
        'date_col': 'ngay_dat_hang',
        'money_col': 'thanh_tien',
        'status_col': 'trang_thai',
        'order_id_col': 'ma_don_hang',
    }
    if not table_profiles or tbl not in table_profiles:
      return cols_info

    profile_cols = table_profiles[tbl].get('columns', {})
    col_names = list(profile_cols.keys())

    # 1. Date column
    for c in col_names:
      c_low = c.lower()
      if any(
          w in c_low
          for w in [
              'thoi_gian',
              'ngay_thang',
              'ngay_giao_dich',
              'ngay_dat',
              'ngay_ban',
              'ngay_nhap',
              'ngay',
              'date',
          ]
      ):
        cols_info['date_col'] = c
        break

    # 2. Money / Amount column
    for c in col_names:
      c_low = c.lower()
      if any(
          w in c_low
          for w in [
              'tong_tien_hang',
              'tong_tien',
              'thanh_tien',
              'tri_gia',
              'can_tra_ncc',
              'so_tien',
              'gia_ban',
          ]
      ):
        cols_info['money_col'] = c
        break

    # 3. Status column
    for c in col_names:
      c_low = c.lower()
      if any(
          w in c_low
          for w in ['trang_thai', 'status', 'ket_qua', 'tinh_trang', 'state']
      ):
        cols_info['status_col'] = c
        break

    # 4. Order ID column
    for c in col_names:
      c_low = c.lower()
      if any(
          w in c_low
          for w in [
              'ma_hoa_don',
              'ma_don_hang',
              'ma_nhap_hang',
              'so_phieu',
              'order_id',
              'ma_bill',
              'ma_giao_dich',
          ]
      ):
        cols_info['order_id_col'] = c
        break

    return cols_info

  @classmethod
  def select_recommended_table(
      cls,
      question: str,
      temporal_anchors: Dict[str, Any],
      table_profiles: Optional[Dict[str, Any]] = None,
      available_tables: Optional[List[str]] = None,
  ) -> Optional[str]:
    """Select the best matching table based on question intent and period overlap."""
    tables = list(table_profiles.keys()) if table_profiles else (available_tables or [])
    if not tables:
      return None

    q_low = question.lower()

    # Intent detection
    is_import = any(w in q_low for w in ['nhập hàng', 'nhap hang', 'phiếu nhập', 'phieu nhap', 'mua hàng', 'ncc', 'nhà cung cấp'])
    is_inventory = any(w in q_low for w in ['tồn kho', 'ton kho', 'hết hạn', 'hsd', 'còn tồn'])
    is_medicine = any(w in q_low for w in ['thuốc', 'thuoc', 'hoạt chất', 'hoat chat', 'kê đơn', 'ke don'])
    is_customer = any(w in q_low for w in ['khách hàng', 'khach hang', 'sinh nhật', 'cccd', 'điểm'])
    is_expense = any(w in q_low for w in ['chi phí', 'chi phi', 'sổ chi', 'tiền điện', 'tiền nước'])

    # Filter candidates based on domain
    if is_import:
      candidates = [t for t in tables if any(w in t.lower() for w in ['nhap', 'mua'])]
    elif is_inventory:
      candidates = [t for t in tables if any(w in t.lower() for w in ['ton', 'kho', 'lo'])]
    elif is_medicine:
      candidates = [t for t in tables if any(w in t.lower() for w in ['thuoc', 'duoc'])]
    elif is_customer:
      candidates = [t for t in tables if any(w in t.lower() for w in ['khach'])]
    elif is_expense:
      candidates = [t for t in tables if any(w in t.lower() for w in ['chi'])]
    else:
      candidates = [t for t in tables if any(w in t.lower() for w in ['ban_hang', 'hoa_don', 'don_hang', 'ban', 'order'])]

    if not candidates:
      candidates = tables

    # Period matching if date window is available
    window = temporal_anchors.get('primary_window')
    if window and table_profiles:
      s_date, e_date = window
      overlapping = []
      for c in candidates:
        p = table_profiles.get(c, {})
        min_d, max_d = p.get('min_date'), p.get('max_date')
        if min_d and max_d:
          # Check date overlap: query start <= table max AND query end >= table min
          if s_date <= max_d and e_date >= min_d:
            overlapping.append((c, p.get('rows', 0)))
        else:
          overlapping.append((c, p.get('rows', 0)))

      if overlapping:
        overlapping.sort(key=lambda x: x[1], reverse=True)
        return overlapping[0][0]

    # Default to candidate with most rows
    if table_profiles:
      ranked = sorted(candidates, key=lambda c: table_profiles.get(c, {}).get('rows', 0), reverse=True)
      return ranked[0]
    return candidates[0]

  @classmethod
  def get_few_shot_examples(cls, cols_info: Optional[Dict[str, str]] = None) -> str:
    tbl = cols_info['tbl'] if cols_info else 'don_hang_chi_tiet'
    date_col = cols_info['date_col'] if cols_info else 'ngay_dat_hang'
    money_col = cols_info['money_col'] if cols_info else 'thanh_tien'
    status_col = cols_info['status_col'] if cols_info else 'trang_thai'
    order_id_col = cols_info['order_id_col'] if cols_info else 'ma_don_hang'

    return f"""### VÍ DỤ MINH HỌA CẤU TRÚC TRUY VẤN:

Ví dụ 1: "Tổng doanh thu trong ngày hôm nay là bao nhiêu?" (as_of_date: 2025-04-30)
```python
def solve(con):
    # Đơn doanh thu: không huỷ, không trả, dùng SUBSTRING để bao quát cả TIMESTAMP
    query = \"\"\"
    SELECT COALESCE(SUM({money_col}), 0)
    FROM {tbl}
    WHERE SUBSTRING(CAST({date_col} AS VARCHAR), 1, 10) = '2025-04-30'
      AND LOWER({status_col}) NOT LIKE '%hu%'
      AND LOWER({status_col}) NOT LIKE '%hủy%'
      AND LOWER({status_col}) NOT LIKE '%cancel%'
      AND LOWER({status_col}) NOT LIKE '%tr%'
      AND LOWER({status_col}) NOT LIKE '%trả%'
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
        COUNT(DISTINCT {order_id_col}) AS total_orders,
        COUNT(DISTINCT CASE WHEN (
            LOWER({status_col}) LIKE '%hu%' OR 
            LOWER({status_col}) LIKE '%hủy%' OR 
            LOWER({status_col}) LIKE '%huỷ%' OR 
            LOWER({status_col}) LIKE '%cancel%'
        ) THEN {order_id_col} END) AS cancelled_orders
    FROM {tbl}
    WHERE SUBSTRING(CAST({date_col} AS VARCHAR), 1, 10) >= '2025-06-01'
      AND SUBSTRING(CAST({date_col} AS VARCHAR), 1, 10) <= '2025-06-30'
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
      available_tables: Optional[List[str]] = None,
      table_profiles: Optional[Dict[str, Any]] = None,
      enable_reasoning: bool = False,
  ) -> str:
    """Generate master prompt combining schema, rules, temporal anchors, table routing, and user question."""
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

    # Select recommended table based on intent and period overlap
    rec_tbl = cls.select_recommended_table(
        question=question,
        temporal_anchors=temporal_anchors,
        table_profiles=table_profiles,
        available_tables=available_tables,
    )
    cols_info = cls.detect_table_columns(rec_tbl, table_profiles) if rec_tbl else None
    few_shots = cls.get_few_shot_examples(cols_info)

    rec_str = ""
    if cols_info:
      rec_str = f"""### GỢI Ý BẢNG VÀ CỘT PHÙ HỢP:
- Bảng gợi ý chính: `{cols_info['tbl']}`
- Cột ngày gợi ý: `{cols_info['date_col']}` | Cột tiền/giá trị: `{cols_info['money_col']}` | Cột trạng thái: `{cols_info['status_col']}` | Cột mã đơn: `{cols_info['order_id_col']}`
"""

    prompt = f"""{cls.SYSTEM_PROMPT}

{schema_context}

{rules_summary}

{few_shots}

{rec_str}
### THÔNG TIN THỜI GIAN ĐÃ XÁC ĐỊNH:
- Ngày mốc (as_of_date): {as_of_date}
{temp_context_str}

### CÂU HỎI CỦA NGƯỜI DÙNG:
\"{question}\" (as_of_date: {as_of_date})
"""
    if enable_reasoning:
      prompt += """
### HƯỚNG DẪN SUY LUẬN TỪNG BƯỚC (REASONING PROCESS):
Trước khi viết mã Python, bạn BẮT BUỘC phải suy luận logic nghiệp vụ từng bước bên trong thẻ <reasoning> ... </reasoning>:
1. Phân tích câu hỏi: Cần tính chỉ số gì? Kiểu đáp án mong đợi là gì (number, percent, date, string, boolean, list, table)?
2. Mốc thời gian: as_of_date là bao nhiêu? Khoảng ngày [từ ngày ... đến ngày ...] là gì? Kiểm tra kỳ hỏi có nằm ngoài dữ liệu (Rule 7) không?
3. Bảng và Cột: Chọn bảng phù hợp từ CƠ SỞ DỮ LIỆU CỬA HÀNG ở trên. Xác định tên cột ngày, cột tiền, cột trạng thái, mã đơn.
4. Quy tắc nghiệp vụ & SQL: Lọc đơn hủy/trả thế nào? Cần lọc dấu tiếng Việt ra sao? Có cần ORDER BY và LIMIT không?
5. Xử lý ngoại lệ: Nếu bảng không có dữ liệu phù hợp hoặc kỳ hỏi nằm ngoài phạm vi, trả về {"type": "unanswerable", "reason": "..."}.

Sau khi kết thúc </reasoning>, viết khối mã Python duy nhất trong ```python ... ```:
"""
    else:
      prompt += """
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
