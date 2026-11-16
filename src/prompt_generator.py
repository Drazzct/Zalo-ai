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
   - Doanh thu: Chỉ tính các đơn không huỷ và không trả hàng (đơn có trả một phần cũng bỏ cả đơn). Bằng tổng thành tiền các dòng (đã trừ giảm giá dòng, không trừ voucher đơn, không gồm VAT/ship). Đơn có trạng thái 'Đã hoàn thành' hoặc 'Hoàn thành' là đơn THÀNH CÔNG hợp lệ, TUYỆT ĐỐI KHÔNG loại bỏ!
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
   - ⚠️ CẢNH BÁO TỬ HUYỆT 'HOÀN THÀNH' vs 'HOÀN TRẢ/HOÀN HÀNG':
     Trong phần mềm bán hàng SME (KiotViet, Sapo, iPOS...), trạng thái đơn hàng thành công phổ biến nhất là 'Đã hoàn thành' hoặc 'Hoàn thành'.
     TUYỆT ĐỐI KHÔNG BAO GIỜ viết `NOT LIKE '%hoàn%'` trần trụi! Viết `NOT LIKE '%hoàn%'` sẽ loại bỏ 100% các đơn 'Đã hoàn thành' hợp lệ, khiến doanh thu/sản lượng luôn ra 0!
     Khi loại trừ đơn hoàn trả, BẮT BUỘC viết:
     `AND LOWER(col) NOT LIKE '%hoàn trả%' AND LOWER(col) NOT LIKE '%hoàn hàng%' AND LOWER(col) NOT LIKE '%trả hàng%' AND (LOWER(col) NOT LIKE '%hoàn%' OR LOWER(col) LIKE '%hoàn thành%')`
     Tương tự, TUYỆT ĐỐI KHÔNG dùng `NOT LIKE '%hu%'` (vì dính chữ 'chuyển' trong 'vận chuyển') và KHÔNG dùng `NOT LIKE '%tr%'` (vì dính 'trong ngày', 'trực tiếp')!
   - Xử lý Tiếng Việt có dấu trong SQL: Từ "hủy" chứa ký tự "ủ" KHÔNG khớp với "u" trong LIKE '%hu%'!
     Khi lọc đơn hủy, BẮT BUỘC kiểm tra cả dấu và không dấu:
     `(LOWER(col) LIKE '%hủy%' OR LOWER(col) LIKE '%huỷ%' OR LOWER(col) LIKE '%da huy%' OR LOWER(col) LIKE '%huy don%' OR LOWER(col) LIKE '%cancel%')`
     Khi tính Doanh thu / Sản lượng bán, MẪU LỌC ĐƠN HỢP LỆ CHUẨN:
     `AND LOWER(col) NOT LIKE '%hủy%' AND LOWER(col) NOT LIKE '%huỷ%' AND LOWER(col) NOT LIKE '%cancel%' AND LOWER(col) NOT LIKE '%trả%' AND LOWER(col) NOT LIKE '%hoàn trả%' AND LOWER(col) NOT LIKE '%hoàn hàng%' AND (LOWER(col) NOT LIKE '%hoàn%' OR LOWER(col) LIKE '%hoàn thành%') AND LOWER(col) NOT LIKE '%không giao được%' AND LOWER(col) NOT LIKE '%that bai%' AND LOWER(col) NOT LIKE '%thất bại%'`
   - Lọc Thuốc và Hoạt chất (Nhà thuốc):
      Hoạt chất trong database có thể là đơn chất (ví dụ: 'Natri clorid') hoặc đa chất phối hợp nối bằng ' + ' (ví dụ: 'Natri clorid + Kali clorid + Natri citrat + Glucose').
      Khi câu hỏi hỏi về một hoạt chất cụ thể (ví dụ: "Thuốc có hoạt chất Natri clorid"), BẮT BUỘC so sánh bằng chính xác:
      `LOWER(TRIM(th.hoat_chat)) = 'natri clorid'`
      TUYỆT ĐỐI KHÔNG dùng `LIKE '%natri clorid%'` vì sẽ bị cộng nhầm doanh thu của các thuốc phối hợp khác!
   - Tỉ lệ huỷ đơn (CỰC KỲ QUAN TRỌNG):
      Tử số CHỈ tính đơn có trạng thái HUỶ (chứa 'hủy', 'huỷ', 'cancel', 'da huy', 'huy don').
      TUYỆT ĐỐI KHÔNG viết `LIKE '%trả%'` hay `LIKE '%hoàn%'` trong CASE WHEN của tử số đơn huỷ! Đơn trả hàng nằm ở mẫu số (tổng đơn), KHÔNG PHẢI đơn hủy!
   - So sánh Thời gian/Ngày: Cột ngày trong database có thể là VARCHAR hoặc TIMESTAMP chứa cả giờ phút ('YYYY-MM-DD HH:MM:SS').
     Khi so sánh hoặc lọc theo ngày, BẮT BUỘC dùng:
     `SUBSTRING(CAST(col AS VARCHAR), 1, 10) = 'YYYY-MM-DD'`
     hoặc trong khoảng ngày:
     `SUBSTRING(CAST(col AS VARCHAR), 1, 10) >= 'YYYY-MM-DD' AND SUBSTRING(CAST(col AS VARCHAR), 1, 10) <= 'YYYY-MM-DD'`
     TUYỆT ĐỐI KHÔNG dùng so sánh bằng trực tiếp `col = 'YYYY-MM-DD'` nếu cột chứa giờ phút.
   - Bảng chia theo thời gian hoặc nghiệp vụ: Nếu shop có nhiều bảng (ví dụ bảng năm 2025 và bảng năm 2026, hoặc bảng bán hàng vs bảng nhập hàng), hãy đọc kỹ phần "GỢI Ý BẢNG VÀ CỘT PHÙ HỢP" và khoảng ngày (Kỳ) của từng bảng để chọn đúng bảng.
    - Đếm số đơn thoả mãn điều kiện gom nhóm (GROUP BY ... HAVING):
      Khi đếm số lượng đơn hàng có tổng tiền/doanh thu thoả mãn điều kiện (ví dụ: có doanh thu từ X đồng trở lên), BẮT BUỘC dùng Subquery đếm bên ngoài:
      `SELECT COUNT(*) FROM (SELECT ma_don_hang FROM <bảng> WHERE ... GROUP BY ma_don_hang HAVING SUM(thanh_tien) >= X)`
      TUYỆT ĐỐI KHÔNG viết `SELECT COUNT(DISTINCT ma_don_hang) ... GROUP BY ma_don_hang HAVING ...` vì GROUP BY sẽ làm mỗi nhóm COUNT luôn chỉ bằng 1!
    - Xử lý cột tiền/số lượng lưu dưới dạng VARCHAR có dấu phẩy:
      Trong DuckDB, các cột chứa số tiền có thể được lưu là chuỗi (VARCHAR) và chứa dấu phân cách hàng nghìn (ví dụ: '227,262,100').
      Khi tính SUM, BẮT BUỘC phải làm sạch chuỗi và ép kiểu sang số:
      `SUM(CAST(REPLACE(CAST(col AS VARCHAR), ',', '') AS DOUBLE))`
      TUYỆT ĐỐI KHÔNG gọi `SUM(col)` trực tiếp nếu cột là kiểu VARCHAR vì DuckDB sẽ báo lỗi `BinderException: No function matches 'sum(VARCHAR)'`!
    - TUYỆT ĐỐI KHÔNG dùng try...except để nuốt lỗi SQL:
      Không bọc `try ... except Exception: return {"type": "unanswerable", "reason": ...}` để giấu lỗi truy vấn SQL! Hãy để code thực thi bình thường để nếu có nhầm tên cột/bảng, hệ thống sẽ tự động bắt được lỗi và phản hồi để bạn sửa đúng ngay lập tức.
5. THUẬT NGỮ & TỪ VIẾT TẮT THƯƠNG MẠI SME:
   Người dùng có thể dùng từ viết tắt thông dụng của chủ shop / nhân viên:
   - `dthu`, `dt`: doanh thu
   - `sl`, `slg`: số lượng
   - `dg`: đơn giá
   - `sp`, `mh`, `hh`: sản phẩm, mặt hàng, hàng hoá
   - `dvt`: đơn vị tính
   - `ncc`: nhà cung cấp
   - `kh`: khách hàng
   - `nv`: nhân viên
   - `hd`, `hđ`: hoá đơn, đơn hàng
   - `pn`: phiếu nhập
   - `hnay`, `hqua`: hôm nay, hôm qua
   - `trc`, `truoc`: trước
   - `thg`, `th`: tháng; `tuan`, `t`: tuần
   - `k`, `ng` = nghìn (x 1,000); `tr` = triệu (x 1,000,000)
   Hãy tự động hiểu đúng ý nghĩa nghiệp vụ của các từ viết tắt này khi phân tích câu hỏi.
"""

  @classmethod
  def detect_table_columns(
      cls, tbl: str, table_profiles: Optional[Dict[str, Any]]
  ) -> Dict[str, Optional[str]]:
    """Detect primary date, money, status, order_id, product, and qty columns for a table."""
    cols_info = {
        'tbl': tbl,
        'date_col': None,
        'money_col': None,
        'status_col': None,
        'order_id_col': None,
        'product_col': None,
        'qty_col': None,
        'unit_price_col': None,
        'unit_col': None,
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
      if c_low in ['tt', 'amount', 'tien'] or any(
          w in c_low
          for w in [
              'tong_tien_hang',
              'tong_tien',
              'thanh_tien',
              'tong_phieu',
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
    if not cols_info['status_col']:
      for c in col_names:
        if c.lower() in ['ghi_chu', 'note', 'trang_thai_xu_ly']:
          cols_info['status_col'] = c
          break

    # 4. Order ID column
    for c in col_names:
      c_low = c.lower()
      if c_low in ['hd', 'so_hd', 'stt', 'ma_don', 'so_don'] or any(
          w in c_low
          for w in [
              'ma_hoa_don',
              'ma_don_hang',
              'ma_don',
              'ma_nhap_hang',
              'so_phieu',
              'order_id',
              'ma_bill',
              'ma_giao_dich',
          ]
      ):
        cols_info['order_id_col'] = c
        break

    # 5. Product name column
    for c in col_names:
      c_low = c.lower()
      if any(
          w in c_low
          for w in [
              'ma_',
              'id',
              'dat_hang',
              'don_hang',
              'nhap_hang',
              'giao_hang',
              'ban_hang',
              'phieu',
              'khach',
          ]
      ):
        continue
      if c_low in ['hang', 'san_pham', 'product'] or any(
          w in c_low
          for w in [
              'ten_san_pham',
              'ten_hang',
              'hang_ban',
              'hang_hoa',
              'mat_hang',
              'dien_giai',
              'ten_thuoc',
              'ten_mon',
              'ten_dv',
          ]
      ):
        cols_info['product_col'] = c
        break

    # 6. Quantity column
    for c in col_names:
      c_low = c.lower()
      if c_low in ['sl', 'qty'] or any(
          w in c_low
          for w in [
              'so_luong_san_pham',
              'so_luong_giao',
              'so_luong_ban',
              'so_luong_nhap',
              'so_luong',
              'sl_ban',
              'sl_nhap',
              'sl_giao',
              'sl_quy_doi',
              'sl_thuc',
              'quantity',
          ]
      ):
        cols_info['qty_col'] = c
        break

    # 7. Unit price column
    for c in col_names:
      c_low = c.lower()
      if c_low == 'dg' or any(
          w in c_low
          for w in [
              'gia_1_dv',
              'don_gia',
              'gia_ban',
              'gia_nhap',
              'gia_san_pham',
              'gia_cu',
              'gia_moi',
              'gia_von',
          ]
      ):
        cols_info['unit_price_col'] = c
        break

    # 8. Unit column
    for c in col_names:
      c_low = c.lower()
      if any(
          w in c_low
          for w in [
              'dvt',
              'don_vi_tinh',
              'dv_goc',
              'loai_dv',
              'don_vi',
              'unit',
          ]
      ):
        cols_info['unit_col'] = c
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
    is_revenue_or_sales = any(w in q_low for w in ['doanh thu', 'bán được', 'ban duoc', 'bán', 'tiền', 'doanh so', 'dthu', 'đơn', 'don', 'chai'])
    is_import = any(w in q_low for w in ['nhập hàng', 'nhap hang', 'phiếu nhập', 'phieu nhap', 'mua hàng', 'ncc', 'nhà cung cấp', 'nhập vào', 'nhập'])
    is_inventory = any(w in q_low for w in ['tồn kho', 'ton kho', 'hết hạn', 'hsd', 'còn tồn'])
    is_medicine = any(w in q_low for w in ['thuốc', 'thuoc', 'hoạt chất', 'hoat chat', 'kê đơn', 'ke don'])
    is_customer = any(w in q_low for w in ['khách hàng', 'khach hang', 'sinh nhật', 'cccd', 'điểm'])
    is_expense = any(w in q_low for w in ['chi phí', 'chi phi', 'sổ chi', 'tiền điện', 'tiền nước'])

    # Filter candidates based on domain
    if is_import:
      if any(w in q_low for w in ['giá', 'gia', 'bình quân', 'mì', 'omachi', 'sản phẩm', 'mặt hàng']):
        candidates = [t for t in tables if any(w in t.lower() for w in ['chi_tiet_nhap', 'ct_nhap', 'nhap_hang_chi_tiet'])]
        if not candidates:
          candidates = [t for t in tables if any(w in t.lower() for w in ['nhap', 'mua'])]
      else:
        candidates = [t for t in tables if any(w in t.lower() for w in ['nhap', 'mua'])]
    elif is_medicine and not is_revenue_or_sales:
      candidates = [t for t in tables if any(w in t.lower() for w in ['thuoc', 'duoc'])]
    elif is_inventory:
      candidates = [t for t in tables if any(w in t.lower() for w in ['ton', 'kho', 'lo'])]
    elif is_customer:
      candidates = [t for t in tables if any(w in t.lower() for w in ['khach'])]
    elif is_expense:
      candidates = [t for t in tables if any(w in t.lower() for w in ['chi'])]
    else:
      candidates = [t for t in tables if any(w in t.lower() for w in ['chi_tiet_hoa_don', 'hoa_don_chi_tiet', 'don_hang_chi_tiet', 'ban_theo_lo', 'ban_hang', 'hoa_don', 'don_hang', 'ban', 'order'])]

    if not candidates:
      candidates = tables

    # Period matching if date window is available
    window = temporal_anchors.get('primary_window')
    if window and table_profiles:
      s_date, e_date = window
      has_overlap = []
      no_date = []
      for c in candidates:
        p = table_profiles.get(c, {})
        min_d, max_d = p.get('min_date'), p.get('max_date')
        if min_d and max_d:
          # Check date overlap: query start <= table max AND query end >= table min
          if s_date <= max_d and e_date >= min_d:
            has_overlap.append((c, p.get('rows', 0)))
        else:
          no_date.append((c, p.get('rows', 0)))

      if has_overlap:
        has_overlap.sort(key=lambda x: x[1], reverse=True)
        return has_overlap[0][0]
      if no_date:
        no_date.sort(key=lambda x: x[1], reverse=True)
        return no_date[0][0]

    # Default to candidate with most rows
    if table_profiles:
      ranked = sorted(candidates, key=lambda c: table_profiles.get(c, {}).get('rows', 0), reverse=True)
      return ranked[0]
    return candidates[0]

  @classmethod
  def get_few_shot_examples(cls, target_table: str = None) -> str:
    tbl = target_table if target_table else "ban_hang"
    return f"""### VÍ DỤ MINH HỌA CẤU TRÚC TRUY VẤN:
(LƯU Ý: BẮT BUỘC dùng đúng tên bảng thực tế trong phần "GỢI Ý BẢNG VÀ CỘT PHÙ HỢP" hoặc "CƠ SỞ DỮ LIỆU CỬA HÀNG" ở trên. TUYỆT ĐỐI KHÔNG tự bịa tên bảng!)

Ví dụ 1: "Tổng doanh thu trong ngày hôm nay là bao nhiêu?" (as_of_date: 2025-04-30)
```python
def solve(con):
    # Đơn doanh thu: không huỷ, không trả, đơn hoàn thành hợp lệ, dùng SUBSTRING để bao quát cả TIMESTAMP
    query = \"\"\"
    SELECT COALESCE(SUM(thanh_tien), 0)
    FROM {tbl}
    WHERE SUBSTRING(CAST(ngay_dat_hang AS VARCHAR), 1, 10) = '2025-04-30'
      AND LOWER(trang_thai) NOT LIKE '%hủy%'
      AND LOWER(trang_thai) NOT LIKE '%huỷ%'
      AND LOWER(trang_thai) NOT LIKE '%cancel%'
      AND LOWER(trang_thai) NOT LIKE '%trả%'
      AND LOWER(trang_thai) NOT LIKE '%hoàn trả%'
      AND LOWER(trang_thai) NOT LIKE '%hoàn hàng%'
      AND (LOWER(trang_thai) NOT LIKE '%hoàn%' OR LOWER(trang_thai) LIKE '%hoàn thành%')
      AND LOWER(trang_thai) NOT LIKE '%không giao được%'
      AND LOWER(trang_thai) NOT LIKE '%thất bại%'
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
    # CHÚ Ý: Tử số CHỈ tính đơn bị HUỶ (không cộng đơn trả). Mẫu số là tổng tất cả các đơn.
    query = \"\"\"
    SELECT 
        COUNT(DISTINCT ma_don_hang) AS total_orders,
        COUNT(DISTINCT CASE WHEN (
            LOWER(trang_thai) LIKE '%hủy%' OR 
            LOWER(trang_thai) LIKE '%huỷ%' OR 
            LOWER(trang_thai) LIKE '%cancel%' OR
            LOWER(trang_thai) LIKE '%da huy%' OR
            LOWER(trang_thai) LIKE '%huy don%'
        ) THEN ma_don_hang END) AS cancelled_orders
    FROM {tbl}
    WHERE SUBSTRING(CAST(ngay_dat_hang AS VARCHAR), 1, 10) >= '2025-06-01'
      AND SUBSTRING(CAST(ngay_dat_hang AS VARCHAR), 1, 10) <= '2025-06-30'
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
    few_shots = cls.get_few_shot_examples(target_table=cols_info.get('tbl') if cols_info else rec_tbl)

    q_low = question.lower()
    is_revenue_or_sales = any(w in q_low for w in ['doanh thu', 'bán được', 'ban duoc', 'bán', 'tiền', 'doanh so', 'dthu', 'đơn', 'don', 'chai'])
    is_import = any(w in q_low for w in ['nhập hàng', 'nhap hang', 'phiếu nhập', 'phieu nhap', 'mua hàng', 'ncc', 'nhà cung cấp', 'nhập vào', 'nhập'])
    is_medicine = any(w in q_low for w in ['thuốc', 'thuoc', 'hoạt chất', 'hoat chat', 'kê đơn', 'ke don'])

    join_hints = []
    if is_medicine and is_revenue_or_sales:
      join_hints.append(
          "- 💊 **Câu hỏi về thuốc/hoạt chất và bán hàng/doanh thu**: Bắt buộc JOIN bảng bán hàng (chi tiết hóa đơn / đơn hàng) với bảng thuốc (`ban_hang_thuoc` hoặc `du_lieu_xuat_danh_sach_thuoc`). LƯU Ý ĐẶC BIỆT KHI JOIN: Nếu bảng bán hàng có `ten_san_pham` mà bảng thuốc chỉ có `ma_sku` (như ở shop `biz_121`), BẮT BUỘC JOIN qua bảng sản phẩm trung gian (`danh_sach_san_pham`) bằng `ten_san_pham`, rồi mới JOIN sang bảng thuốc bằng `ma_sku`! Cột thuốc kê đơn là `thuoc_ke_don = TRUE` (hoặc `ke_don = TRUE`). Với hoạt chất cụ thể, so sánh bằng chính xác: `LOWER(TRIM(hoat_chat)) = 'tên_hoạt_chất'` (KHÔNG dùng LIKE để tránh dính thuốc phối hợp). Loại trừ đơn hủy, trả, và 'không giao được'."
      )
    if is_import and any(w in q_low for w in ['mì', 'omachi', 'sản phẩm', 'bình quân', 'mặt hàng', 'gia']):
      join_hints.append(
          "- 📦 **Câu hỏi về giá nhập sản phẩm cụ thể**: Hãy JOIN bảng chi tiết nhập hàng (`chi_tiet_nhap_hang`) với bảng sản phẩm (`danh_sach_san_pham`) qua `ma_hang` để lọc theo tên mặt hàng (`ten_hang`). Giá nhập bình quân một đơn vị = `ROUND(SUM(so_luong * don_gia) / SUM(so_luong))`."
      )

    # Category / Group Query Hint
    is_category = any(w in q_low for w in ['nhóm', 'nhom', 'loại', 'loai', 'ngành', 'nganh', 'danh mục', 'danh muc', 'chủng loại', 'đồ dùng', 'do dung', 'sữa', 'sua'])
    if is_category and table_profiles and rec_tbl:
      rec_cols = table_profiles.get(rec_tbl, {}).get('columns', {})
      has_cat = any(any(k in c.lower() for k in ['nhom', 'loai', 'category', 'nganh']) for c in rec_cols)
      if not has_cat:
        for other_tbl, p in table_profiles.items():
          if other_tbl == rec_tbl:
            continue
          other_cols = p.get('columns', {})
          cat_col = next((c for c in other_cols if any(k in c.lower() for k in ['nhom', 'loai_hang', 'category', 'nganh'])), None)
          if cat_col:
            join_key = next((c for c in rec_cols if c in other_cols and any(k in c.lower() for k in ['hang', 'san_pham', 'sku', 'ma_'])), None)
            if not join_key:
              for r_c in rec_cols:
                for o_c in other_cols:
                  if r_c == o_c or (('hang' in r_c or 'san_pham' in r_c) and ('hang' in o_c or 'san_pham' in o_c)):
                    join_key = (r_c, o_c)
                    break
                if join_key:
                  break
            if join_key:
              if isinstance(join_key, tuple):
                join_cond = f"{rec_tbl}.{join_key[0]} = {other_tbl}.{join_key[1]}"
              else:
                join_cond = f"{rec_tbl}.{join_key} = {other_tbl}.{join_key}"
              join_hints.append(
                  f"- 🏷️ **Câu hỏi về nhóm hàng / danh mục**: Bảng `{rec_tbl}` không có cột nhóm hàng. BẮT BUỘC JOIN `{rec_tbl}` với `{other_tbl}` qua điều kiện `{join_cond}` để lọc theo nhóm `{other_tbl}.{cat_col}` (Ví dụ: `WHERE LOWER({other_tbl}.{cat_col}) LIKE '%...%'`)."
              )
            break

    # Pipe bundle conversion for dev_004 or pipe queries
    if any(w in q_low for w in ['ống pvc', 'ong pvc', 'bình minh', 'binh minh']) or (cols_info and cols_info.get('tbl') == 'so_ban_hang'):
      if any(w in q_low for w in ['cây', 'cay', 'ống', 'ong', 'bao nhiêu']):
        join_hints.append(
            "- 📏 **Quy đổi bó Ống PVC**: Các mặt hàng Ống PVC Bình Minh bán theo bó (1 bó = 10 cây). Khi tính số lượng cây, nếu dòng ghi đơn vị bó (`LOWER(dvt) LIKE '%bó%'` hoặc `dvt = 'bó'`), số cây = `sl_ban * 10`; nếu ghi `cây`, số cây = `sl_ban` (Dùng: `CASE WHEN LOWER(dvt) LIKE '%bó%' THEN sl_ban * 10 ELSE sl_ban END`)."
        )

    # Mother & Baby valid sales row filter
    if cols_info and cols_info.get('tbl') in ['ban_hang_2025', 'ban_hang_2026']:
      join_hints.append(
          "- 🍼 **Lọc dòng hàng hợp lệ**: Trong bảng bán hàng, chỉ tính các dòng là hàng hóa thật (loại trừ các dòng chiết khấu / phụ thu: `WHERE ten_hang NOT IN ('Voucher', 'Phí ship') AND ten_hang NOT LIKE '%điểm%'`)."
      )

    # dev_002 beverage filter
    if cols_info and 'ban_hang_t' in cols_info.get('tbl', ''):
      if any(w in q_low for w in ['trà', 'tra', 'cà phê', 'ca phe', 'món', 'ly']):
        join_hints.append(
            "- ☕ **Nhóm đồ uống**: Để lọc theo nhóm (như nhóm trà, cà phê), lọc theo cột tên hàng: `WHERE LOWER(ten_san_pham) LIKE '%trà%'` (hoặc `LIKE '%tra%'`)."
        )

    rec_str = ""
    if cols_info and cols_info.get('tbl'):
      items = [f"Bảng giao dịch/dữ liệu gợi ý: `{cols_info['tbl']}`"]
      if cols_info.get('date_col'):
        items.append(f"Cột ngày: `{cols_info['date_col']}`")
      if cols_info.get('money_col'):
        items.append(f"Cột tiền/giá trị: `{cols_info['money_col']}`")
      if cols_info.get('status_col'):
        items.append(f"Cột trạng thái: `{cols_info['status_col']}`")
      if cols_info.get('order_id_col'):
        items.append(f"Cột mã đơn: `{cols_info['order_id_col']}`")
      if cols_info.get('product_col'):
        items.append(f"Cột tên hàng/sản phẩm: `{cols_info['product_col']}`")
      if cols_info.get('qty_col'):
        items.append(f"Cột số lượng: `{cols_info['qty_col']}`")
      if cols_info.get('unit_price_col'):
        items.append(f"Cột đơn giá: `{cols_info['unit_price_col']}`")
      if cols_info.get('unit_col'):
        items.append(f"Cột đơn vị tính: `{cols_info['unit_col']}`")
      rec_str = f"### GỢI Ý BẢNG VÀ CỘT PHÙ HỢP:\n- {' | '.join(items)}\n"
      if join_hints:
        rec_str += '\n'.join(join_hints) + '\n'

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
### HƯỚNG DẪN SUY LUẬN TỪNG BƯỚC (<reasoning>):
Chỉ được suy luận TỐI ĐA 2 ĐẾN 3 DÒNG GẠCH ĐẦU DÒNG (DƯỚI 40 TỪ) bên trong thẻ <reasoning> ... </reasoning>:
- Chỉ số & Kiểu đáp án: (ví dụ: doanh thu, number)
- Bảng & Khoảng ngày: (ví dụ: ban_hang_2025, từ YYYY-MM-DD đến YYYY-MM-DD)
- Điều kiện lọc: (ví dụ: bỏ đơn huỷ/trả, giữ đơn hoàn thành hợp lệ)

⛔ LỆNH CẤM NGHIÊM NGẶT ĐỂ TRÁNH CẮT CỤT MÃ (TRUNCATION):
1. TUYỆT ĐỐI KHÔNG viết nháp mã SQL hoặc code Python bên trong thẻ reasoning!
2. TUYỆT ĐỐI KHÔNG phân tích giả định dài dòng!
3. ĐÓNG THẺ </reasoning> NGAY LẬP TỨC sau 3 dòng gạch đầu dòng trên để dành token cho mã Python!
4. Khối Python ```python def solve(con): ... ``` BẮT BUỘC viết hoàn chỉnh ngay sau thẻ </reasoning>.

Viết thẻ <reasoning> ngắn gọn, sau đó viết hàm solve(con) trong ```python ... ```:
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
    err_low = error_message.lower()
    if "does not exist" in err_low:
      hint = "\nLƯU Ý ĐẶC BIỆT: Bảng hoặc cột trên không tồn tại trong database của shop! Vui lòng đọc kỹ danh sách bảng và cột thực tế trong phần CƠ SỞ DỮ LIỆU CỬA HÀNG ở trên để dùng đúng bảng có thật.\n"
    elif "solve(con)" in err_low:
      hint = "\nLƯU Ý ĐẶC BIỆT: Mã nguồn của bạn chưa định nghĩa hàm `solve(con)` hoặc bị ngắt quãng giữa chừng do token limit! Vui lòng BỎ QUA REASONING, viết trực tiếp khối mã Python ```python def solve(con): ... ``` hoàn chỉnh ngay!\n"
    elif "syntaxerror" in err_low or "unterminated" in err_low or "never closed" in err_low:
      hint = "\nLƯU Ý ĐẶC BIỆT: Mã nguồn của bạn bị lỗi cú pháp hoặc bị ngắt nửa chừng (truncated)! Vui lòng KHÔNG giải thích reasoning nữa, hãy viết NGAY khối mã Python ```python def solve(con): ... ``` ngắn gọn, đầy đủ, đóng ngoặc cẩn thận.\n"

    displayed_code = previous_code.strip() if previous_code.strip() else "# (Chưa có mã nguồn hợp lệ nào được sinh ra)"

    base_prompt = original_prompt
    for marker in [
        "### QUY TẮC BẮT BUỘC VỀ SUY LUẬN",
        "### HƯỚNG DẪN SUY LUẬN TỪNG BƯỚC (REASONING PROCESS):",
    ]:
      if marker in base_prompt:
        base_prompt = base_prompt.split(marker)[0].strip()

    reflection = f"""{base_prompt}

### MÃ BẠN ĐÃ VIẾT TRƯỚC ĐÓ (GẶP LỖI):
```python
{displayed_code}
```

### THÔNG BÁO LỖI KHI THỰC THI (SANDBOX ERROR):
{error_message}
{hint}
⚠️ YÊU CẦU ĐẶC BIỆT KHI SỬA LỖI (BẮT BUỘC):
- TUYỆT ĐỐI BỎ QUA THẺ <reasoning>! KHÔNG sinh thẻ reasoning để tránh bị ngắt quãng token limit!
- Viết NGAY LẬP TỨC khối mã Python `solve(con)` đã sửa lỗi trong ```python ... ```:
"""
    return reflection
