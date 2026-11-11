# STEP 2 — Manual Question Converter / DataMate `biz_101`

## Phạm vi và độ tin cậy

- **Input thực:** 10/40 câu hỏi thật lấy nguyên văn từ `STEP1/benchmark/questions_biz_101.jsonl`, không tự tạo câu hỏi.
- **Nguồn giải nghĩa:** `STEP1/sources/rulebook.md`, `STEP1/sources/readme.md`, `STEP1/schema.json`, `STEP1/business_rules.json` và tên sản phẩm/đơn vị đã kiểm tra trên `STEP1/biz_101.sqlite`.
- **Đầu ra máy đọc:** `converted_questions.jsonl` (mỗi dòng một JSON object), `converter_mapping.csv`, `converted_question.schema.json`.
- **Tách nhãn:** hoàn toàn không đọc `answers.jsonl`, không chứa đáp án chuẩn, không chứa SQL lời giải mẫu.
- **Giới hạn:** đây là **10 annotation thủ công có thể kiểm chứng**, chưa phải converter tổng quát cho toàn bộ câu hỏi DataMate. `status=ready` chỉ nói input semantic đủ để viết truy vấn, không chứng minh đáp án tương lai sẽ đúng.
- **Quy ước:** `end_date` và `start_date` bao gồm cả ngày biên; `as_of_date` lấy từ record gốc, tuyệt đối không lấy đồng hồ hệ thống.

## Tóm tắt 10 câu đã chuẩn hóa

| # | Question ID | Intent | Khoảng thời gian | Đầu ra | Luật nổi bật |
|---:|---|---|---|---|---|
| 1 | `q_0c8f3e07768f` | `count_distinct(valid_order_count)` | 2025-10-01 → 2025-12-31 | `number` | R01, R02, R04, R05, R10, R11 |
| 2 | `q_0cb7c9b93048` | `count_distinct(valid_order_count)` | 2025-09-23 → 2025-09-23 | `number` | R01, R02, R04, R05, R10, R11 |
| 3 | `q_1cc70c12aa27` | `sum(net_sales_revenue)` | 2026-02-22 → 2026-02-22 | `number` | R01, R02, R03, R05, R10, R11 |
| 4 | `q_20aa992c0d3f` | `argmax_by_group(net_sales_revenue)` | 2026-05-01 → 2026-05-31 | `date` | R01, R02, R03, R05, R10, R11 |
| 5 | `q_38e2b6cef714` | `argmax_by_group(sold_base_quantity)` | 2026-06-01 → 2026-06-30 | `string` | R01, R02, R05, R06, R07, R10, R11 |
| 6 | `q_62a9a454f35b` | `sum(net_sales_revenue)` | 2026-05-01 → 2026-05-31 | `number` | R01, R02, R03, R05, R10, R11 |
| 7 | `q_7c8afb8a81e9` | `sum(sold_base_quantity)` | 2025-07-01 → 2025-07-31 | `number` | R01, R02, R05, R07, R08, R10, R11 |
| 8 | `q_fcbf1e1cd8d4` | `price_observation(unit_selling_price)` | 2025-07-28 → 2025-07-28 | `number` | R01, R05, R07, R09, R10, R11 |
| 9 | `q_c893acce3ef3` | `sum(net_sales_revenue)` | 2026-07-01 → 2026-07-31 | `number` | R01, R02, R03, R05, R10, R11 |
| 10 | `q_15fd3e0d0363` | `sum(net_sales_revenue)` | 2026-02-01 → 2026-02-28 | `number` | R01, R02, R03, R05, R10, R11 |

## Phân tích chi tiết từng câu (semantic → intent → temporal → rule → normalized)

### 1. `q_0c8f3e07768f`

- **Original:** e so don hang quy 4/2025 la bao nhiu vay
- **as_of_date:** `2026-08-24`
- **Semantic analysis:** Đếm hóa đơn bán hợp lệ trong quý IV/2025. Số đơn là số mã hóa đơn phân biệt, không phải số dòng hàng. Quý 4 dương lịch gồm tháng 10–12.
- **Intent:** metric `valid_order_count`, aggregation `count_distinct`, measure `order_id`, GROUP BY `none`, top-k `None`, expected type `number`.
- **Entity:** Toàn cửa hàng (không entity filter).
- **Filters:** `order_date` between_inclusive ['2025-10-01', '2025-12-31'], `order_status` in ['Xong', 'Đang giao'].
- **Temporal normalization:** `quy 4/2025` → **2025-10-01 đến 2025-12-31** (inclusive), theo `calendar_quarter`; anchor `2026-08-24`.
- **Business rules:** **R01** (train/rulebook.md: line 5), **R02** (train/rulebook.md: lines 7-15), **R04** (train/rulebook.md: line 14), **R05** (train/rulebook.md: lines 22-35), **R10** (train/rulebook.md: line 111), **R11** (train/rulebook.md: lines 97-101).
- **Normalized question:** Có bao nhiêu hóa đơn bán hợp lệ được đặt từ 01/10/2025 đến hết 31/12/2025?
- **Ambiguities còn tồn:** Không phát hiện điểm mơ hồ đang chặn conversion.
- **Conditional risks:** Không có điều kiện phát sinh đáng chú ý trong phạm vi converter này.
- **Needs JOIN:** `False`; relation `sales_lines`.

### 2. `q_0cb7c9b93048`

- **Original:** Cho tôi biết số đơn hôm qua.
- **as_of_date:** `2025-09-24`
- **Semantic analysis:** Đếm số đơn trong ngày ngay trước as_of_date của câu hỏi. Hôm qua được neo vào as_of_date=2025-09-24, không neo vào ngày máy chạy chương trình.
- **Intent:** metric `valid_order_count`, aggregation `count_distinct`, measure `order_id`, GROUP BY `none`, top-k `None`, expected type `number`.
- **Entity:** Toàn cửa hàng (không entity filter).
- **Filters:** `order_date` between_inclusive ['2025-09-23', '2025-09-23'], `order_status` in ['Xong', 'Đang giao'].
- **Temporal normalization:** `hôm qua` → **2025-09-23 đến 2025-09-23** (inclusive), theo `relative_previous_day`; anchor `2025-09-24`.
- **Business rules:** **R01** (train/rulebook.md: line 5), **R02** (train/rulebook.md: lines 7-15), **R04** (train/rulebook.md: line 14), **R05** (train/rulebook.md: lines 22-35), **R10** (train/rulebook.md: line 111), **R11** (train/rulebook.md: lines 97-101).
- **Normalized question:** Có bao nhiêu hóa đơn bán hợp lệ được đặt trong ngày 23/09/2025 (hôm qua so với 24/09/2025)?
- **Ambiguities còn tồn:** Không phát hiện điểm mơ hồ đang chặn conversion.
- **Conditional risks:** Không có điều kiện phát sinh đáng chú ý trong phạm vi converter này.
- **Needs JOIN:** `False`; relation `sales_lines`.

### 3. `q_1cc70c12aa27`

- **Original:** Hôm nay cửa hàng bán được bao nhiêu tiền?
- **as_of_date:** `2026-02-22`
- **Semantic analysis:** Cộng doanh thu bán hợp lệ trong ngày tham chiếu. 'Bán được bao nhiêu tiền' là doanh thu thành tiền các dòng, không phải số tiền đã thu.
- **Intent:** metric `net_sales_revenue`, aggregation `sum`, measure `line_amount_vnd`, GROUP BY `none`, top-k `None`, expected type `number`.
- **Entity:** Toàn cửa hàng (không entity filter).
- **Filters:** `order_date` between_inclusive ['2026-02-22', '2026-02-22'], `order_status` in ['Xong', 'Đang giao'].
- **Temporal normalization:** `Hôm nay` → **2026-02-22 đến 2026-02-22** (inclusive), theo `relative_today`; anchor `2026-02-22`.
- **Business rules:** **R01** (train/rulebook.md: line 5), **R02** (train/rulebook.md: lines 7-15), **R03** (train/rulebook.md: lines 11-15), **R05** (train/rulebook.md: lines 22-35), **R10** (train/rulebook.md: line 111), **R11** (train/rulebook.md: lines 97-101).
- **Normalized question:** Doanh thu bán hàng hợp lệ trong ngày 22/02/2026 (hôm nay theo câu hỏi) là bao nhiêu VND?
- **Ambiguities còn tồn:** Không phát hiện điểm mơ hồ đang chặn conversion.
- **Conditional risks:** Không có điều kiện phát sinh đáng chú ý trong phạm vi converter này.
- **Needs JOIN:** `False`; relation `sales_lines`.

### 4. `q_20aa992c0d3f`

- **Original:** thang 5/2026 ngay nao cua hang ban dc nhieu tien nhat
- **as_of_date:** `2026-08-24`
- **Semantic analysis:** Tìm ngày có tổng doanh thu lớn nhất trong tháng 5/2026. Phải SUM doanh thu theo từng ngày rồi lấy ngày đứng đầu; không lấy dòng hàng có thành tiền cao nhất.
- **Intent:** metric `net_sales_revenue`, aggregation `argmax_by_group`, measure `line_amount_vnd`, GROUP BY `order_date`, top-k `1`, expected type `date`.
- **Entity:** Toàn cửa hàng (không entity filter).
- **Filters:** `order_date` between_inclusive ['2026-05-01', '2026-05-31'], `order_status` in ['Xong', 'Đang giao'].
- **Temporal normalization:** `thang 5/2026` → **2026-05-01 đến 2026-05-31** (inclusive), theo `calendar_month`; anchor `2026-08-24`.
- **Business rules:** **R01** (train/rulebook.md: line 5), **R02** (train/rulebook.md: lines 7-15), **R03** (train/rulebook.md: lines 11-15), **R05** (train/rulebook.md: lines 22-35), **R10** (train/rulebook.md: line 111), **R11** (train/rulebook.md: lines 97-101).
- **Normalized question:** Trong tháng 05/2026, ngày nào có tổng doanh thu bán hợp lệ cao nhất? Trả về ngày dương lịch.
- **Ambiguities còn tồn:** Không phát hiện điểm mơ hồ đang chặn conversion.
- **Conditional risks:** If several equal highest-revenue dates occur, rulebook does not explicitly specify day-tie ordering; do not silently choose one.
- **Needs JOIN:** `False`; relation `sales_lines`.

### 5. `q_38e2b6cef714`

- **Original:** Mặt hàng bán chạy nhất tháng 6 năm 2026 là mặt hàng nào vậy?
- **as_of_date:** `2026-08-24`
- **Semantic analysis:** Tìm mặt hàng có số lượng bán quy đổi lớn nhất trong tháng 6/2026. 'Bán chạy nhất' không phải doanh thu cao nhất; phải gộp các biến thể tên chỉ khác hoa thường/khoảng trắng trước khi xếp hạng.
- **Intent:** metric `sold_base_quantity`, aggregation `argmax_by_group`, measure `base_quantity`, GROUP BY `product_name`, top-k `1`, expected type `string`.
- **Entity:** Toàn cửa hàng (không entity filter).
- **Filters:** `order_date` between_inclusive ['2026-06-01', '2026-06-30'], `order_status` in ['Xong', 'Đang giao'].
- **Temporal normalization:** `tháng 6 năm 2026` → **2026-06-01 đến 2026-06-30** (inclusive), theo `calendar_month`; anchor `2026-08-24`.
- **Business rules:** **R01** (train/rulebook.md: line 5), **R02** (train/rulebook.md: lines 7-15), **R05** (train/rulebook.md: lines 22-35), **R06** (train/rulebook.md: lines 38-46, 135-136), **R07** (train/rulebook.md: lines 43-44, 139-142; train/data/biz_101/README.md: Quy ước), **R10** (train/rulebook.md: line 111), **R11** (train/rulebook.md: lines 97-101).
- **Normalized question:** Trong tháng 06/2026, mặt hàng nào bán chạy nhất theo tổng số lượng quy về đơn vị cơ bản của đơn hợp lệ?
- **Ambiguities còn tồn:** Không phát hiện điểm mơ hồ đang chặn conversion.
- **Conditional risks:** Không có điều kiện phát sinh đáng chú ý trong phạm vi converter này.
- **Needs JOIN:** `False`; relation `sales_lines`.

### 6. `q_62a9a454f35b`

- **Original:** Doanh thu của Coca Cola 330ml trong tháng 5 năm 2026 là bao nhiêu?
- **as_of_date:** `2026-08-24`
- **Semantic analysis:** Cộng doanh thu các dòng Coca Cola 330ml trong tháng 5/2026. Tên hàng trong CSV có biến thể gấp đôi khoảng trắng; cả hai phải được coi là cùng một thực thể.
- **Intent:** metric `net_sales_revenue`, aggregation `sum`, measure `line_amount_vnd`, GROUP BY `none`, top-k `None`, expected type `number`.
- **Entity:** Coca Cola 330ml; aliases: Coca  Cola 330ml, Coca Cola 330ml.
- **Filters:** `order_date` between_inclusive ['2026-05-01', '2026-05-31'], `order_status` in ['Xong', 'Đang giao'], `product_name` in ['Coca  Cola 330ml', 'Coca Cola 330ml'].
- **Temporal normalization:** `tháng 5 năm 2026` → **2026-05-01 đến 2026-05-31** (inclusive), theo `calendar_month`; anchor `2026-08-24`.
- **Business rules:** **R01** (train/rulebook.md: line 5), **R02** (train/rulebook.md: lines 7-15), **R03** (train/rulebook.md: lines 11-15), **R05** (train/rulebook.md: lines 22-35), **R10** (train/rulebook.md: line 111), **R11** (train/rulebook.md: lines 97-101).
- **Normalized question:** Doanh thu bán hợp lệ của mặt hàng Coca Cola 330ml (bao gồm biến thể khoảng trắng trong tên) từ 01/05/2026 đến hết 31/05/2026 là bao nhiêu VND?
- **Ambiguities còn tồn:** Không phát hiện điểm mơ hồ đang chặn conversion.
- **Conditional risks:** Không có điều kiện phát sinh đáng chú ý trong phạm vi converter này.
- **Needs JOIN:** `False`; relation `sales_lines`.

### 7. `q_7c8afb8a81e9`

- **Original:** Tháng 7/2025 mặt hàng Nếp cái hoa vàng bán được tổng cộng bao nhiêu kg?
- **as_of_date:** `2026-08-24`
- **Semantic analysis:** Tính tổng khối lượng nếp bán ra theo kg trong tháng 7/2025. Số kg dùng đơn vị cơ bản kg của sản phẩm, không dùng số dòng hoặc tổng doanh thu.
- **Intent:** metric `sold_base_quantity`, aggregation `sum`, measure `base_quantity`, GROUP BY `none`, top-k `None`, expected type `number`.
- **Entity:** Nếp cái hoa vàng; aliases: Nếp cái hoa vàng.
- **Filters:** `order_date` between_inclusive ['2025-07-01', '2025-07-31'], `order_status` in ['Xong', 'Đang giao'], `product_name` in ['Nếp cái hoa vàng'].
- **Temporal normalization:** `Tháng 7/2025` → **2025-07-01 đến 2025-07-31** (inclusive), theo `calendar_month`; anchor `2026-08-24`.
- **Business rules:** **R01** (train/rulebook.md: line 5), **R02** (train/rulebook.md: lines 7-15), **R05** (train/rulebook.md: lines 22-35), **R07** (train/rulebook.md: lines 43-44, 139-142; train/data/biz_101/README.md: Quy ước), **R08** (train/rulebook.md: line 44), **R10** (train/rulebook.md: line 111), **R11** (train/rulebook.md: lines 97-101).
- **Normalized question:** Trong tháng 07/2025, cửa hàng bán hợp lệ tổng cộng bao nhiêu kg mặt hàng Nếp cái hoa vàng, sau khi quy đổi về kg?
- **Ambiguities còn tồn:** Không phát hiện điểm mơ hồ đang chặn conversion.
- **Conditional risks:** Không có điều kiện phát sinh đáng chú ý trong phạm vi converter này.
- **Needs JOIN:** `False`; relation `sales_lines`.

### 8. `q_fcbf1e1cd8d4`

- **Original:** Giá bán một gói Thuốc lá Vinataba vào ngày 28/07/2025 là bao nhiêu?
- **as_of_date:** `2026-08-24`
- **Semantic analysis:** Lấy giá trước chiết khấu tính cho một gói Vinataba tại ngày xác định. Giá đơn vị trước giảm không phải doanh thu chia lượng bán; không loại đơn hủy/trả. Quy đổi nếu bán theo cây.
- **Intent:** metric `unit_selling_price`, aggregation `price_observation`, measure `sale_price_vnd`, GROUP BY `none`, top-k `None`, expected type `number`.
- **Entity:** Thuốc lá Vinataba; aliases: Thuốc lá Vinataba.
- **Filters:** `order_date` between_inclusive ['2025-07-28', '2025-07-28'], `product_name` in ['Thuốc lá Vinataba'].
- **Temporal normalization:** `ngày 28/07/2025` → **2025-07-28 đến 2025-07-28** (inclusive), theo `explicit_day`; anchor `2026-08-24`.
- **Business rules:** **R01** (train/rulebook.md: line 5), **R05** (train/rulebook.md: lines 22-35), **R07** (train/rulebook.md: lines 43-44, 139-142; train/data/biz_101/README.md: Quy ước), **R09** (train/rulebook.md: line 70), **R10** (train/rulebook.md: line 111), **R11** (train/rulebook.md: lines 97-101).
- **Normalized question:** Giá bán ghi trên dòng bán, trước chiết khấu, tính cho một gói Thuốc lá Vinataba vào ngày 28/07/2025 là bao nhiêu VND? Xem cả đơn hủy/trả.
- **Ambiguities còn tồn:** Không phát hiện điểm mơ hồ đang chặn conversion.
- **Conditional risks:** If multiple different historical per-pack prices are observed on the same day, return ambiguity rather than averaging without a source rule.
- **Needs JOIN:** `False`; relation `sales_lines`.

### 9. `q_c893acce3ef3`

- **Original:** Xem giúp tổng doanh thu tháng 7 năm 2026 là bao nhiêu?
- **as_of_date:** `2026-08-24`
- **Semantic analysis:** Cộng doanh thu bán hợp lệ của toàn cửa hàng tháng 7/2026. Toàn shop: không lọc theo mặt hàng hay khách, phải loại nguyên đơn hủy/trả.
- **Intent:** metric `net_sales_revenue`, aggregation `sum`, measure `line_amount_vnd`, GROUP BY `none`, top-k `None`, expected type `number`.
- **Entity:** Toàn cửa hàng (không entity filter).
- **Filters:** `order_date` between_inclusive ['2026-07-01', '2026-07-31'], `order_status` in ['Xong', 'Đang giao'].
- **Temporal normalization:** `tháng 7 năm 2026` → **2026-07-01 đến 2026-07-31** (inclusive), theo `calendar_month`; anchor `2026-08-24`.
- **Business rules:** **R01** (train/rulebook.md: line 5), **R02** (train/rulebook.md: lines 7-15), **R03** (train/rulebook.md: lines 11-15), **R05** (train/rulebook.md: lines 22-35), **R10** (train/rulebook.md: line 111), **R11** (train/rulebook.md: lines 97-101).
- **Normalized question:** Tổng doanh thu bán hợp lệ của cửa hàng từ 01/07/2026 đến hết 31/07/2026 là bao nhiêu VND?
- **Ambiguities còn tồn:** Không phát hiện điểm mơ hồ đang chặn conversion.
- **Conditional risks:** Không có điều kiện phát sinh đáng chú ý trong phạm vi converter này.
- **Needs JOIN:** `False`; relation `sales_lines`.

### 10. `q_15fd3e0d0363`

- **Original:** thang 2/2026 mat hang Thuoc la Vinataba thu ve bao nhieu tien
- **as_of_date:** `2026-08-24`
- **Semantic analysis:** Cộng doanh thu Vinataba trong tháng 2/2026. 'Thu về bao nhiêu tiền' mặc định là doanh thu, không phải tiền đã thanh toán; tháng 02/2026 có 28 ngày.
- **Intent:** metric `net_sales_revenue`, aggregation `sum`, measure `line_amount_vnd`, GROUP BY `none`, top-k `None`, expected type `number`.
- **Entity:** Thuốc lá Vinataba; aliases: Thuốc lá Vinataba.
- **Filters:** `order_date` between_inclusive ['2026-02-01', '2026-02-28'], `order_status` in ['Xong', 'Đang giao'], `product_name` in ['Thuốc lá Vinataba'].
- **Temporal normalization:** `thang 2/2026` → **2026-02-01 đến 2026-02-28** (inclusive), theo `calendar_month`; anchor `2026-08-24`.
- **Business rules:** **R01** (train/rulebook.md: line 5), **R02** (train/rulebook.md: lines 7-15), **R03** (train/rulebook.md: lines 11-15), **R05** (train/rulebook.md: lines 22-35), **R10** (train/rulebook.md: line 111), **R11** (train/rulebook.md: lines 97-101).
- **Normalized question:** Tổng doanh thu bán hợp lệ của mặt hàng Thuốc lá Vinataba từ 01/02/2026 đến hết 28/02/2026 là bao nhiêu VND?
- **Ambiguities còn tồn:** Không phát hiện điểm mơ hồ đang chặn conversion.
- **Conditional risks:** Không có điều kiện phát sinh đáng chú ý trong phạm vi converter này.
- **Needs JOIN:** `False`; relation `sales_lines`.

## Các bẫy ngữ nghĩa đã xử lý

1. **Đơn ≠ dòng hàng:** `COUNT(DISTINCT order_id)` (rulebook §1); loại đơn `Đã hủy`, `Đổi trả` nhưng giữ `Đang giao`.
2. **Doanh thu ≠ giá bán × lượng:** lấy `line_amount_vnd`, đã trừ giảm giá dòng. Không nhầm với số tiền khách trả.
3. **`hôm qua` ≠ ngày hiện tại của máy:** câu `q_0cb7...` neo vào `as_of_date=2025-09-24` nên là `2025-09-23`.
4. **`bán chạy nhất` ≠ doanh thu lớn nhất:** theo `SUM(base_quantity)`, nhóm tên hàng đã chuẩn hóa. Rulebook §9 nêu tie-break theo mã, không có mã thì tên.
5. **Tên sản phẩm không hoàn toàn sạch:** tên Coca có cả `Coca Cola 330ml` và `Coca  Cola 330ml`. Luật §8 cho phép coi các cách viết cùng một vật là cùng một thứ; không dùng exact match 1 tên nếu còn alias.
6. **Giá bán lịch sử ≠ doanh thu:** giá một gói Vinataba là `sale_price_vnd` trước giảm quy về **gói**; tra cả đơn hủy/trả theo rulebook §5. Cảnh báo nếu ngày có nhiều giá khác nhau vì nguồn không chỉ rõ cách lấy duy nhất.
7. **Kg ≠ bao:** `Nếp cái hoa vàng` có đơn vị cơ bản `kg`; dùng `base_quantity`, không cộng số bao hoặc nhân hệ số tùy tiện.
8. **Không tự cho 0 nếu ngoài vùng dữ liệu:** rulebook §7 phân biệt thiếu dữ liệu và số 0.

## Verification — Không dùng đáp án

| Kiểm tra | Kết quả |
|---|---|
| Đối chiếu nguyên văn 10 câu gốc | **10/10** |
| Date ranges, as_of_date, tháng/quý | **10/10** |
| Cột, relation, aggregation hợp lệ | **10/10** |
| Rule IDs có thật trong STEP 1 | **10/10** |
| Tên hàng / alias có trong database | **10/10** |
| Không thêm nhãn đáp án / lời giải SQL | **10/10** |

- Lệnh kiểm tra ở `README.md` gọi `verify_step2.py`: ngoài các mục trên còn kiểm tra **10 invariant ngữ nghĩa đặc thù**.
- Query vào SQLite **chỉ kiểm tra phạm vi dữ liệu và alias**; không tính kết quả cuối, không tra `answers_biz_101.jsonl`.
- `verification.json` ghi kiểm tra từng question ID, các tệp đầu vào theo SHA-256 và chỉ số `distinct_price_levels_for_requested_day` dùng để phát hiện trường hợp giá mơ hồ. Không lưu giá bán thực tế.

## Chuyển giao STEP 3

- `converted_questions.jsonl` là **output của layer Converter**; STEP 3 sẽ kết hợp nó với schema/bảng/quan hệ/business rule context thành `coder_inputs.jsonl`.
- **Prompt Coder không nhận** đường dẫn dữ liệu bí mật, output evaluation, SQL lời giải hoặc `verification.json`.
- STEP 3 phải quy định status handling: `ready` → build input, `needs_clarification` → giữ ambiguity, `unanswerable_candidate` → kiểm tra theo rulebook §7.
- Nếu Nam/Nguyên cung cấp Converter chính thức, họ chỉ cần đáp ứng contract; inference/evaluation không nên phụ thuộc vào cách annotation thủ công.
