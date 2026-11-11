# STEP 1 — Data Dictionary: DataMate biz_101

> Source: `train/data/biz_101/README.md`, `ban_hang.csv`, `train/rulebook.md`. SQLite stage **không** thay đổi raw CSV.

## Hạt dữ liệu (grain)

- Mỗi dòng CSV là một mặt hàng thuộc một đơn, **không phải một đơn**. Một `order_id` xuất hiện nhiều lần.
- `source_csv_line` là khóa dòng kỹ thuật từ vị trí CSV (bắt đầu 2), không phải PK nghiệp vụ.
- `order_date` đã đổi từ `D thg M YYYY` sang `YYYY-MM-DD`, tiền đã bỏ dấu `,` ngăn nghìn.
- `sales_lines_raw`: toàn bộ dòng; view `sales_lines`: không chứa bản ghi export trùng hoàn toàn theo rulebook §8.

## Mapping cột

| Cột nguồn | SQLite | Type | Nulls | Unique | Ý nghĩa (README) |
|---|---|---|---:|---:|---|
| Giá bán | `sale_price_vnd` | INTEGER | 0 | 118 | Đơn giá theo đơn vị bán của dòng, trước giảm |
| Kết quả | `order_status` | TEXT | 0 | 4 | Trạng thái đơn |
| Nội dung | `product_name` | TEXT | 0 | 70 | Tên mặt hàng |
| Ngày tháng | `order_date` | TEXT | 0 | 450 | Ngày bán/ngày đặt |
| Đơn vị (tính) | `unit` | TEXT | 0 | 16 | Đơn vị bán |
| so_luong | `quantity` | INTEGER | 0 | 10 | Số lượng theo đơn vị bán |
| Thanh tien | `line_amount_vnd` | INTEGER | 0 | 392 | Thành tiền dòng sau giảm giá dòng |
| Quy ra ĐV lẻ | `base_quantity` | INTEGER | 0 | 33 | Số lượng đã đổi về đơn vị cơ bản |
| Mã hóa đơn | `order_id` | TEXT | 0 | 22428 | Mã hóa đơn, có thể lặp ở nhiều dòng hàng |
| Đối tác | `customer_name` | TEXT | 0 | 261 | Tên khách, Khách lẻ nếu không lưu |

## Quan hệ

- `sales_lines.order_date` ↔ `calendar.date` theo ngày dương ISO; calendar độc lập, không phải transaction table.
- `sales_lines.order_id` dùng nhóm dòng về đơn, **không unique per row**; status/date/customer nhất quán trong toàn bộ đơn (đã kiểm tra).

## Trạng thái nguồn

| Kết quả | Dòng | Đơn phân biệt | Có tính doanh thu/đếm đơn? |
|---|---:|---:|---|
| Xong | 53893 | 21386 | Có |
| Đang giao | 31 | 10 | Có |
| Đã hủy | 1714 | 699 | Không |
| Đổi trả | 863 | 333 | Không |

## Đơn vị và tiền

- **Đơn giá** (`sale_price_vnd`) không giống **thành tiền** (`line_amount_vnd`). Có chiết khấu từng dòng; phải SUM(line_amount_vnd) khi hỏi doanh thu.
- **Số lượng** (`quantity`) không giống **quy về đơn vị cơ bản** (`base_quantity`). Dùng `base_quantity` cho câu hỏi bán chạy/bán bao nhiêu kg... theo rulebook.
- Chi tiết tất cả hệ số quan sát được trong `data_profile.json: observed_unit_factors`; quy ước chính thống ở README.

## Giới hạn

- Không có bảng chi phí, nhập hàng, tồn kho, công nợ trong biz_101. Không tự suy ra chúng từ bán hàng.
- 70 tên hàng phân biệt; 261 nhãn Đối tác, trong đó có Khách lẻ. Cần bảo vệ dữ liệu khách khi xây prompt.
- Các quy tắc về câu hỏi, trạng thái, thời gian và tie-break phải dùng `business_rules.json` kết hợp rulebook gốc.
- Không được đưa `evaluation_only/answers_biz_101.jsonl` vào context của model.
