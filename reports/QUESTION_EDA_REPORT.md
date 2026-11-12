# 📊 BÁO CÁO PHÂN TÍCH KHÁM PHÁ DỮ LIỆU CÂU HỎI (QUESTION EDA)
> **Zalo AI Challenge 2026 - DataMate Track**  
> Thời gian tạo báo cáo: 2026-11-09

---

## 1. TỔNG QUAN TẬP CÂU HỎI (DATASET OVERVIEW)

| Tiêu chí | Tập Huấn Luyện (Train) | Tập Kiểm Thử (Public Test) |
| :--- | :--- | :--- |
| **Tổng số câu hỏi** | **3,000 câu** | **1,000 câu** |
| **Số lượng shop (business_id)** | **30 shops** | **14 shops** |
| **Số câu trung bình / shop** | 100.0 câu/shop | 71.4 câu/shop |
| **Khoảng ngày mốc (`as_of_date`)** | 2025-01-15 đến 2026-09-20 | 2025-02-04 đến 2026-09-30 |

> 💡 **Nhận xét:**
> - Mỗi shop trong tập Train có đúng **100 câu hỏi** phân bố đồng đều cho 30 shop (từ `biz_101` đến `biz_130`).
> - Tập Public Test có 14 shop, mỗi shop ~71 câu hỏi.
> - `as_of_date` trải dài gần 2 năm (2025 - cuối 2026), đòi hỏi logic tính toán mốc thời gian tương đối ("hôm nay", "hôm qua", "tháng này") phải luôn bám chặt vào `as_of_date`.

---

## 2. PHÂN BỐ CÁC KIỂU ĐÁP ÁN (ANSWER TYPES DISTRIBUTION)

Phân tích trên 3.000 câu hỏi tập Train:

| Kiểu đáp án (`type`) | Số lượng câu hỏi | Tỷ lệ (%) | Ví dụ đặc trưng |
| :--- | :---: | :---: | :--- |
| **`number`** | **1,884** | **62.8%** | Tổng doanh thu, tổng số lượng hàng, số đơn hàng |
| **`percent`** | **578** | **19.3%** | Tỉ lệ huỷ đơn (%), % tăng trưởng doanh thu so với kỳ trước |
| **`list`** | **193** | **6.4%** | Top 3 mặt hàng bán chạy nhất, danh sách mã đơn hủy |
| **`date`** | **145** | **4.8%** | Ngày bán chạy nhất tháng, ngày đầu tiên nhập hàng X |
| **`string`** | **88** | **2.9%** | Tên sản phẩm bán chạy nhất, tên khách mua nhiều nhất |
| **`unanswerable`** | **70** | **2.3%** | Câu hỏi ngoài khoảng ngày dữ liệu (Rule 7), thiếu bảng |
| **`boolean`** | **23** | **0.8%** | "Có đơn hàng nào trong ngày... không?" (True / False) |
| **`table`** | **19** | **0.6%** | Bảng tổng kết doanh thu và số đơn theo từng chi nhánh |

> ⚠️ **Insight cốt lõi:**
> 1. **Dạng số chiếm áp đảo:** `number` + `percent` chiếm hơn **82.1%** tổng số câu hỏi!
> 2. **Cơ chế Abstain (Unanswerable):** Chiếm **2.3%** (70 câu). Nếu câu hỏi hỏi một khoảng thời gian mà database shop hoàn toàn chưa có dữ liệu, model phải trả về `unanswerable` để nhận trọn 1 điểm, tránh bị trừ -1 điểm.

---

## 3. PHÂN LOẠI CHỦ ĐỀ & NGHIỆP VỤ CÂU HỎI (INTENT & DOMAIN TAXONOMY)

| Nhóm nghiệp vụ / Chủ đề | Số câu (Train) | Tỷ lệ (%) | Số câu (Public Test) | Trọng tâm phân tích SQL / DuckDB |
| :--- | :---: | :---: | :---: | :--- |
| **Doanh thu & Bán hàng** | 1402 | 46.7% | 436 | Lọc bảng và cột tương ứng |
| **Hủy đơn & Hoàn trả** | 171 | 5.7% | 24 | Lọc bảng và cột tương ứng |
| **Mặt hàng bán chạy & Số lượng** | 149 | 5.0% | 55 | Lọc bảng và cột tương ứng |
| **Công nợ & Khách hàng** | 106 | 3.5% | 45 | Lọc bảng và cột tương ứng |
| **Chuyên ngành Dược phẩm** | 100 | 3.3% | 20 | Lọc bảng và cột tương ứng |
| **Nhập hàng & Nhà cung cấp** | 58 | 1.9% | 9 | Lọc bảng và cột tương ứng |
| **Thời trang / Size / Màu sắc** | 52 | 1.7% | 14 | Lọc bảng và cột tương ứng |
| **Tồn kho & Hạn dùng (HSD)** | 27 | 0.9% | 12 | Lọc bảng và cột tương ứng |
| **Thu chi & Lợi nhuận** | 25 | 0.8% | 10 | Lọc bảng và cột tương ứng |

---

## 4. PHÂN TÍCH CÁC MỐC THỜI GIAN TRONG CÂU HỎI (TEMPORAL ANCHORS)

Hệ thống ghi nhận sự phân bổ các mốc thời gian:

| Dạng mốc thời gian | Tần suất xuất hiện (câu) | Tỷ lệ (%) | Quy tắc ánh xạ (Temporal Mapping) |
| :--- | :---: | :---: | :--- |
| **Tháng (tháng này / tháng trước / tháng X/YYYY)** | 2063 | 68.8% | Ánh xạ qua `CalendarResolver` & `as_of_date` |
| **Hôm nay / Hôm qua / Ngày cụ thể** | 601 | 20.0% | Ánh xạ qua `CalendarResolver` & `as_of_date` |
| **Quý & Năm** | 334 | 11.1% | Ánh xạ qua `CalendarResolver` & `as_of_date` |
| **Tuần (tuần này / tuần trước / tuần thứ X)** | 76 | 2.5% | Ánh xạ qua `CalendarResolver` & `as_of_date` |
| **Ca làm việc (Ca sáng / Ca chiều)** | 60 | 2.0% | Ánh xạ qua `CalendarResolver` & `as_of_date` |
| **Dịp lễ / Tết** | 6 | 0.2% | Ánh xạ qua `CalendarResolver` & `as_of_date` |

---

## 5. ĐẶC ĐIỂM NGÔN NGỮ, TEENCODE & CHỮ VIẾT TẮT (TEENCODE & SLANG)

Chủ shop SME Việt Nam thường xuyên nhập câu hỏi bằng văn phong giao tiếp nhanh, viết tắt, hoặc gõ không dấu:

| Hiện tượng ngôn ngữ | Số lượng câu phát hiện | Mẫu ví dụ trong dữ liệu thực tế | Cách xử lý trong Pipeline |
| :--- | :---: | :--- | :--- |
| **`bao nhiu` / `nhiu` / `bn`** | 422 | *"tháng này tổng giá trị các phiếu nhập hàng là bao nhiu"* | Chuẩn hóa regex về "bao nhiêu" |
| **`dthu` / `d thu`** | 482 | *"thang 7/2026 co bao nhiu don co dthu tu 55.000 dong tro len"* | Chuẩn hóa thành "doanh thu" |
| **Tiếng Việt KHÔNG DẤU** | 650 | *"thang 7/2026 co bao nhiu don co dthu..."* | `QueryNormalizer` phục hồi dấu & entity |
| **`ncc` (Nhà cung cấp)** | 0 | *"tổng tiền nhập hàng từ ncc tháng này"* | Tự động route sang bảng nhập hàng |
| **`ko` / `k` (không)** | 17 | *"mặt hàng nào ko bán được"* | Nhận diện phủ định (NOT IN / NOT LIKE) |

---

## 6. MA TRẬN MỐI QUAN HỆ: CHỦ ĐỀ CÂU HỎI ➔ KIỂU ĐÁP ÁN (TOPIC TO ANSWER TYPE)

| Nhóm chủ đề | `number` | `percent` | `list` | `date` | `string` | `unanswerable` | `boolean` | `table` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Doanh thu & Bán hàng** | 861 | 339 | 45 | 114 | 5 | 15 | 23 | 0 |
| **Hủy đơn & Hoàn trả** | 70 | 101 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Mặt hàng bán chạy & Số lượng** | 72 | 3 | 51 | 0 | 17 | 1 | 0 | 5 |
| **Công nợ & Khách hàng** | 53 | 0 | 28 | 0 | 3 | 6 | 0 | 16 |
| **Chuyên ngành Dược phẩm** | 69 | 23 | 6 | 1 | 0 | 1 | 0 | 0 |
| **Nhập hàng & Nhà cung cấp** | 51 | 0 | 0 | 0 | 5 | 2 | 0 | 0 |
| **Thời trang / Size / Màu sắc** | 48 | 3 | 0 | 0 | 0 | 1 | 0 | 0 |
| **Tồn kho & Hạn dùng (HSD)** | 15 | 0 | 5 | 4 | 0 | 3 | 0 | 0 |
| **Thu chi & Lợi nhuận** | 5 | 0 | 13 | 0 | 6 | 1 | 0 | 0 |
| **Chuyên ngành Điện tử / Xe máy** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

---

## 7. CHI TIẾT CÁC CÂU HỎI KHÔNG THỂ TRẢ LỜI (UNANSWERABLE QUESTIONS)

Có **70 câu hỏi (2.3%)** trong tập huấn luyện có nhãn `unanswerable`:
- **Nguyên nhân chính 1 (Quy tắc Rule 7):** Câu hỏi truy vấn thời gian nằm HOÀN TOÀN ngoài khoảng dữ liệu của cửa hàng (ví dụ: dữ liệu shop chỉ đến tháng 12/2025, nhưng câu hỏi hỏi về tháng 03/2026).
- **Nguyên nhân chính 2:** Dữ liệu hoàn toàn trống trong kỳ hỏi (ví dụ: không có bất kỳ hóa đơn nào trong tuần đó để tính tỷ lệ).
- **Ví dụ tiêu biểu trong tập Train:**
- `q_03a446be8b75` (biz_121): "trong thang 2/2025, ti le don huy la bao nhieu %" (as_of_date: 2026-09-20)
- `q_04128078842a` (biz_118): "cửa hàng có mấy khách nhà ở đường Hai Bà Trưng" (as_of_date: 2026-09-10)
- `q_05a8b30443a1` (biz_130): "trong so khach da mua hang thang 7/2026, bnhiu % mua tu 8 don tro len" (as_of_date: 2026-08-29)
- `q_147e7a072dc7` (biz_106): "Tháng 2/2025 doanh thu thay đổi bao nhiêu % so với tháng liền trước?" (as_of_date: 2026-09-14)
- `q_1af6e691fc94` (biz_106): "Ai là người lành nghề nhất trong số nhân viên?" (as_of_date: 2026-09-14)

---

## 8. KẾT LUẬN & ĐỀ XUẤT CHO PIPELINE SUY LUẬN

1. **Table Routing là chìa khóa:** Với các câu hỏi về nhập hàng, ncc, thuốc, bảo hành, xe máy, pipeline cần route ngay vào đúng bảng nghiệp vụ (không query nhầm bảng `ban_hang`).
2. **Xử lý triệt để Teencode & Tiếng Việt có dấu trong SQL:**
   - Trong SQL, chữ `"hủy"` có dấu `ủ` không khớp với `LIKE '%hu%'`. Bắt buộc kiểm tra `(LOWER(status) LIKE '%hu%' OR LOWER(status) LIKE '%hủy%')`.
3. **Cơ chế Abstain Gate:** Giúp bảo toàn điểm số bằng cách bắt các câu hỏi kỳ ngoài khoảng dữ liệu và trả về `unanswerable` thay vì đoán bừa để bị phạt -1 điểm.
