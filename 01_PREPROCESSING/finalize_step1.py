import json,re,sqlite3
from pathlib import Path
p=Path(__file__).resolve().parent
prof=json.loads((p/'data_profile.json').read_text(encoding='utf-8'))
readme=(p/'sources/readme.md').read_text(encoding='utf-8')
rulebook=(p/'sources/rulebook.md').read_text(encoding='utf-8')
map_cols={'Giá bán':'sale_price_vnd','Kết quả':'order_status','Nội dung':'product_name','Ngày tháng':'order_date','Đơn vị (tính)':'unit','so_luong':'quantity','Thanh tien':'line_amount_vnd','Quy ra ĐV lẻ':'base_quantity','Mã hóa đơn':'order_id','Đối tác':'customer_name'}
def save(n,d): (p/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
columns=[]
for original,converted in map_cols.items():
 x=prof['column_profiles'][original]
 columns.append({'name':converted,'source_name':original,'sqlite_type':'INTEGER' if converted in ('sale_price_vnd','quantity','line_amount_vnd','base_quantity') else 'TEXT','non_null':True,'distinct_values':x['unique'],'missing_values':x['null'],'example':x['examples'][0]['value'],'source':'train/data/biz_101/ban_hang.csv + README.md'})
columns.extend([{'name':'source_csv_line','source_name':None,'sqlite_type':'INTEGER','description':'Original CSV line position, starting from 2, primary key of staging; not business primary key'}, {'name':'is_duplicate_export','source_name':None,'sqlite_type':'INTEGER','description':'1 for repeated identical source record within same order, 0 otherwise; all currently 0'}])
schema={'schema_version':'step1.0','business_id':'biz_101','engine':'sqlite','database_path':'biz_101.sqlite','source_csv':'train/data/biz_101/ban_hang.csv','grain':'one item line per order; order_id repeats across lines','tables':[{'name':'sales_lines_raw','type':'table','primary_key':['source_csv_line'],'columns':columns,'source':'all 56501 data rows'},{'name':'sales_lines','type':'view','columns':[c for c in columns if c['name']!='is_duplicate_export'],'definition':'SELECT from sales_lines_raw WHERE is_duplicate_export=0','source':'deduplicated view mandated by rulebook §8 (zero duplicates found)'},{'name':'calendar','type':'table','primary_key':['date'],'columns':[{'name':x,'source_name':x,'sqlite_type':'TEXT' if x in ('date','holiday') else 'INTEGER'} for x in ('date','weekday','lunar_day','lunar_month','lunar_year','lunar_leap','holiday')],'source':'train/calendar.csv'}],'relationships':[{'from':'sales_lines.order_date','to':'calendar.date','type':'date lookup','confidence':'verified date format/domain; not declared FK'}],'candidate_business_keys':[{'columns':['order_id'],'grain':'order, NOT unique per line','confidence':'verified by grouping; no FK declared'}],'source_to_target_mapping':map_cols,'validation':{'rows':prof['rows'],'orders':prof['distinct_orders'],'date_range':[prof['date_min'],prof['date_max']],'parse_errors':len(prof['parse_errors'])},'remarks':['SQLite logical date values are ISO-8601 TEXT; sources remain unchanged in sources/','Do not send database file path as an instruction to the model; executor reads it locally','Do not confuse candidate order key with unique row key','No unobserved tables such as inventory, purchases, payments are created']}
save('schema.json',schema)

def rule(i,topic,text,where,applies=True,confidence='verified_source_rule'):
 return {'id':i,'topic':topic,'rule':text,'evidence':where,'applicability_to_biz_101':applies,'confidence':confidence}
rules=[
 rule('R01','date_anchor','Cụm hôm nay/hôm qua/tháng này dựa trên questions.as_of_date; dữ liệu sau as_of_date không được tính cho câu hỏi as-of.','train/rulebook.md: introduction'),
 rule('R02','revenue_filter','Loại toàn bộ order có trạng thái hủy hoặc đổi trả, kể cả trả một phần; đang giao vẫn tính. Biz_101: Xong/Đang giao được tính, Đã hủy/Đổi trả bị loại.','train/rulebook.md: §1; train/data/biz_101/ban_hang.csv: Kết quả'),
 rule('R03','revenue_metric','Doanh thu = SUM(Thanh tien) các dòng của đơn hợp lệ, không phải SUM(Giá bán × so_luong); không cộng phí vận chuyển hay VAT, không trừ voucher cấp đơn nếu có.','train/rulebook.md: §1; train/data/biz_101/README.md: Thanh tien'),
 rule('R04','order_count','COUNT(DISTINCT Mã hóa đơn) trên các đơn không hủy và không trả, trong khoảng ngày đặt.','train/rulebook.md: §1; train/data/biz_101/README.md: Mã hóa đơn/Ngày tháng'),
 rule('R05','time_bounds','Khoảng từ X đến Y bao gồm cả hai; N ngày gần nhất kể cả hôm nay; tuần bắt đầu thứ Hai; tháng này kết thúc ở as_of_date.','train/rulebook.md: §2'),
 rule('R06','top_items','Bán chạy xếp theo SUM(Quy ra ĐV lẻ) của đơn hợp lệ, không theo doanh thu. Tie-break theo mã rồi tên nếu không có mã.','train/rulebook.md: §3 and §9; train/data/biz_101/README.md: Quy ra ĐV lẻ'),
 rule('R07','unit_conversion','Quy ra ĐV lẻ là số lượng đã quy đổi; hệ số theo từng mặt hàng và đơn vị trong README, không áp hệ số cố định toàn cửa hàng.','train/data/biz_101/README.md: Quy ước; train/rulebook.md: §10'),
 rule('R08','unit_specific_quantity','Nếu hỏi bán bao nhiêu kg, cộng lượng đã quy đổi của sản phẩm có đơn vị cơ bản kg; không mặc định mọi sản phẩm đều là kg.','train/rulebook.md: §3; train/data/biz_101/README.md: quy đổi gạo'),
 rule('R09','selling_price','Giá bán một đơn vị cơ bản vào ngày D dùng đơn giá trước discount của dòng bán, kể cả hủy/trả; phải quy đổi nếu dòng theo bao/lốc/thùng.','train/rulebook.md: §5'),
 rule('R10','identical_export','Hai dòng cùng order và đồng nhất ở mọi cột nguồn tính một lần; ở biz_101 kiểm tra thấy 0 dòng dư dạng này.','train/rulebook.md: §8; computed profiler'),
 rule('R11','no_data','Kỳ hoàn toàn ngoài phạm vi ngày có dữ liệu hoặc yêu cầu thông tin không được lưu có thể là unanswerable, không coi tự động là 0.','train/rulebook.md: §7'),
 rule('R12','reference_output','Nhãn type là number/date/string… theo answers.jsonl nhưng nhãn chỉ dùng evaluation; date ISO-8601, tiền số nguyên VND.','train/rulebook.md: §9; train/answers.jsonl'),
 rule('R13','customer_identity','Vì biz_101 không có mã khách, nhóm theo tên trên đơn, cần xử lý những tên chỉ khác cách viết; Khách lẻ không được tính như một khách có danh tính.','train/rulebook.md: §3; train/data/biz_101/README.md: Đối tác'),
 rule('R14','calendar','Tết Âm lịch theo các mốc 23 Chạp đến 10 Giêng đọc từ train/calendar.csv; không sử dụng tính toán ngày âm phỏng đoán.','train/rulebook.md: §2; train/calendar.csv'),
 rule('R15','rounding','Tiền làm tròn đồng theo rulebook; trung bình tiền làm tròn nửa đồng lên; percent thường 2 chữ số thập phân.','train/rulebook.md: §3; §9'),
]
save('business_rules.json',{'business_id':'biz_101','rulebook_sha256':next(x['sha256'] for x in json.loads((p/'inventory.json').read_text())['archive_members'] if x['logical_name']=='rulebook'),'rules':rules,'important_gaps':['No cost/inventory/receivables tables in business 101','No explicit unique order-line ID in source','Source lacks declared foreign keys','No official Docker contest guideline contained in train.zip']})

lines=['# STEP 1 — Data Dictionary: DataMate biz_101','', '> Source: `train/data/biz_101/README.md`, `ban_hang.csv`, `train/rulebook.md`. SQLite stage **không** thay đổi raw CSV.','', '## Hạt dữ liệu (grain)','', '- Mỗi dòng CSV là một mặt hàng thuộc một đơn, **không phải một đơn**. Một `order_id` xuất hiện nhiều lần.','- `source_csv_line` là khóa dòng kỹ thuật từ vị trí CSV (bắt đầu 2), không phải PK nghiệp vụ.','- `order_date` đã đổi từ `D thg M YYYY` sang `YYYY-MM-DD`, tiền đã bỏ dấu `,` ngăn nghìn.', '- `sales_lines_raw`: toàn bộ dòng; view `sales_lines`: không chứa bản ghi export trùng hoàn toàn theo rulebook §8.','', '## Mapping cột','', '| Cột nguồn | SQLite | Type | Nulls | Unique | Ý nghĩa (README) |','|---|---|---|---:|---:|---|']
descriptions={'Giá bán':'Đơn giá theo đơn vị bán của dòng, trước giảm','Kết quả':'Trạng thái đơn','Nội dung':'Tên mặt hàng','Ngày tháng':'Ngày bán/ngày đặt','Đơn vị (tính)':'Đơn vị bán','so_luong':'Số lượng theo đơn vị bán','Thanh tien':'Thành tiền dòng sau giảm giá dòng','Quy ra ĐV lẻ':'Số lượng đã đổi về đơn vị cơ bản','Mã hóa đơn':'Mã hóa đơn, có thể lặp ở nhiều dòng hàng','Đối tác':'Tên khách, Khách lẻ nếu không lưu'}
for x in columns[:10]:
 a=x['source_name'];lines.append(f"| {a} | `{x['name']}` | {x['sqlite_type']} | {x['missing_values']} | {x['distinct_values']} | {descriptions[a]} |")
lines += ['','## Quan hệ','', '- `sales_lines.order_date` ↔ `calendar.date` theo ngày dương ISO; calendar độc lập, không phải transaction table.', '- `sales_lines.order_id` dùng nhóm dòng về đơn, **không unique per row**; status/date/customer nhất quán trong toàn bộ đơn (đã kiểm tra).','', '## Trạng thái nguồn','', '| Kết quả | Dòng | Đơn phân biệt | Có tính doanh thu/đếm đơn? |','|---|---:|---:|---|']
for s in ['Xong','Đang giao','Đã hủy','Đổi trả']:
 lines.append(f"| {s} | {prof['statuses_by_line'].get(s,0)} | {prof['statuses_by_order_consistent_only'].get(s,0)} | {'Có' if s in ('Xong','Đang giao') else 'Không'} |")
lines += ['','## Đơn vị và tiền','', '- **Đơn giá** (`sale_price_vnd`) không giống **thành tiền** (`line_amount_vnd`). Có chiết khấu từng dòng; phải SUM(line_amount_vnd) khi hỏi doanh thu.', '- **Số lượng** (`quantity`) không giống **quy về đơn vị cơ bản** (`base_quantity`). Dùng `base_quantity` cho câu hỏi bán chạy/bán bao nhiêu kg... theo rulebook.', '- Chi tiết tất cả hệ số quan sát được trong `data_profile.json: observed_unit_factors`; quy ước chính thống ở README.','', '## Giới hạn','', '- Không có bảng chi phí, nhập hàng, tồn kho, công nợ trong biz_101. Không tự suy ra chúng từ bán hàng.', '- 70 tên hàng phân biệt; 261 nhãn Đối tác, trong đó có Khách lẻ. Cần bảo vệ dữ liệu khách khi xây prompt.', '- Các quy tắc về câu hỏi, trạng thái, thời gian và tie-break phải dùng `business_rules.json` kết hợp rulebook gốc.', '- Không được đưa `evaluation_only/answers_biz_101.jsonl` vào context của model.','']
(p/'data_dictionary.md').write_text('\n'.join(lines),encoding='utf-8')

v=json.loads((p/'verification.json').read_text())
report=f'''# DataMate — STEP 1 hoàn tất: biz_101

## Phạm vi và nguồn

- Archive gốc: `train.zip`; tất cả 6 file nền đã đọc và lưu trong `sources/` (README, CSV, rulebook, calendar, questions, answers).
- Business ID thực tế: **`biz_101`**; `train/data/biz_101/` gồm **`README.md`** và **`ban_hang.csv`**.
- Gắn nhãn lĩnh vực: cửa hàng bán lẻ/tạp hóa (suy luận từ danh mục hàng hóa, không phải nhãn ngành chính thức).
- Thời gian ghi nhận trong CSV: **{prof['date_min']} → {prof['date_max']}**. README ghi dữ liệu có đến hết 24/08/2026.
- `train/calendar.csv` có **{prof['calendar_rows']}** ngày, từ {prof['calendar_date_range'][0]} đến {prof['calendar_date_range'][1]}.
- `train/questions.jsonl` và `train/answers.jsonl` gồm toàn bộ business; lọc theo `business_id=\"biz_101\"` được **40 câu** và **40 nhãn đối chiếu**.

## Kết quả profiling trên dữ liệu thật

| Metric | Giá trị |
|---|---:|
| Data rows | {prof['rows']:,} |
| Columns | {prof['cols']} |
| Distinct `Mã hóa đơn` | {prof['distinct_orders']:,} |
| Tên mặt hàng | {prof['distinct_products']} |
| Nhãn khách (`Đối tác`, gồm Khách lẻ) | {prof['distinct_customers_including_walk_in']} |
| Ngày bán phân biệt | {prof['unique_dates']} |
| Exact duplicate extra lines (cùng toàn bộ 10 cột nguồn) | {prof['exact_duplicate_extra_lines']} |
| Đơn có status/date/customer không nhất quán qua các dòng | {prof['orders_with_inconsistent_attributes_count']} |
| Parse errors ngày/số | {len(prof['parse_errors'])} |
| Dòng có số lượng âm/0 hoặc tiền âm | {prof['invalid_or_negative_qty_price_amount_count']} |
| Dòng có thành tiền > giá bán × lượng | {prof['money_greater_than_qty_times_unit_price_count']} |
| Nhóm sản phẩm+đơn vị có hệ số chuyển đổi biến thiên | {len(prof['varying_unit_factors'])} |
| Dòng có chiết khấu (thành tiền < giá × lượng) | 698 |

### Trạng thái đơn

| Status | Dòng hàng | Số đơn |
|---|---:|---:|
| Xong | {prof['statuses_by_line']['Xong']:,} | {prof['statuses_by_order_consistent_only']['Xong']:,} |
| Đang giao | {prof['statuses_by_line']['Đang giao']:,} | {prof['statuses_by_order_consistent_only']['Đang giao']:,} |
| Đã hủy | {prof['statuses_by_line']['Đã hủy']:,} | {prof['statuses_by_order_consistent_only']['Đã hủy']:,} |
| Đổi trả | {prof['statuses_by_line']['Đổi trả']:,} | {prof['statuses_by_order_consistent_only']['Đổi trả']:,} |

Không đếm dòng thành số đơn. Theo rulebook §1, đơn đổi trả bị loại **cả đơn** khỏi doanh thu/đếm đơn, kể cả trả một phần; đơn đang giao vẫn tính.

### Trường dữ liệu thực có

{', '.join('`'+k+'`' for k in map_cols)}.

**Kiểm chứng đặc biệt:** `Nếp cái hoa vàng` xuất hiện trong source dù README tập trung giải thích quy đổi các mặt hàng khác; không nên xây từ điển sản phẩm chỉ từ README. `Thuốc lá Vinataba` có cả giá theo `cây` và `gói`; câu hỏi hỏi giá mỗi gói phải dùng đúng giá gói/cách quy đổi, không trả giá theo cây. Nhiều dòng có giảm giá thực tế, không dùng phép nhân đơn giá × lượng thay `Thanh tien`.

## Schema SQLite được tạo

- `sales_lines_raw` giữ nguyên mọi dòng, mapping cột được ghi rõ trong `schema.json`.
- View `sales_lines` áp quy tắc chống dòng xuất trùng trong cùng đơn, ở file này không phát hiện duplicate.
- `calendar` giữ cột nguồn, tham chiếu ngày với `sales_lines.order_date`.
- SQLite `PRAGMA integrity_check`: **{v['sqlite_integrity']}**; tổng dòng staging **{v['raw_rows_sqlite']:,}**; view **{v['dedup_rows_sqlite']:,}**.
- Không tạo bảng tưởng tượng cho kho, giá vốn, chi phí, nợ hoặc lịch sử giá.

## Business semantics quan trọng

1. **Thời gian tương đối** lấy từ `as_of_date` của từng câu hỏi, không lấy giờ hiện tại trên máy.
2. **Đếm đơn**: `COUNT(DISTINCT order_id)` sau khi lọc status, không `COUNT(*)`.
3. **Doanh thu**: `SUM(line_amount_vnd)` với status `Xong`/`Đang giao`; mỗi dòng CSV là một item line, đã gồm chiết khấu dòng.
4. **Bán chạy**: theo `SUM(base_quantity)` (đơn vị cơ bản), không theo doanh thu.
5. **Giá bán ngày D**: nguồn `Giá bán` là giá theo đơn vị bán; quy về đơn vị cơ bản, tính cả đơn huỷ/trả, theo rulebook §5.
6. **Không có dữ liệu ≠ 0** nếu hỏi ngoài phạm vi hoặc hỏi metric thiếu nguồn (rulebook §7).
7. **Tên khách** dùng như khóa nghiệp vụ khi thiếu mã khách, nhưng không coi `Khách lẻ` là một khách danh tính.
8. **Chống leakage**: chỉ sử dụng questions khi tạo coder inputs; answers ở `evaluation_only/`.

## Các vấn đề cần lưu ý

- Không có PK nghiệp vụ từng dòng; `source_csv_line` chỉ là khóa staging tự tạo.
- Không có FK declared trong CSV; quan hệ ngày → calendar là phép lookup kiểm chứng, không phải FK khai báo.
- Không biết dữ liệu ngoài khoảng 2025-06-01…2026-08-24, cần tuân thủ unanswerable.
- Câu hỏi giá tại ngày D cần xem có nhiều mức giá theo nhiều đơn/hình thức bán không, không được tự chọn MAX/MIN khi không có căn cứ.
- `schema.json` không chứa đáp án; file answers tách để tránh leakage.
- `train.zip` chứa rulebook chứ **không** chứa Docker guideline chính thức của BTC, nên chưa xác minh luật triển khai Docker bằng nguồn này.

## Verification & reproducibility

Chạy `python analyze_step1.py train.zip` trong thư mục gói; SQLite được tạo lại từ dữ liệu gốc. Kiểm tra: `python -m sqlite3 biz_101.sqlite 'SELECT COUNT(*) FROM sales_lines;'` nếu Python hỗ trợ CLI sqlite3; hoặc dùng script Python ở README.

STEP 1 đủ để chuyển sang STEP 2 (manual question converter) sau khi review các rules và chọn 5–10 câu thật trong `benchmark/questions_biz_101.jsonl`.
'''
(p/'STEP1_REPORT.md').write_text(report,encoding='utf-8')
readme2='''# DataMate biz_101 — Reproducible STEP 1 bundle

Dùng Python 3.10+; chỉ Python standard library, không cần GPU/Docker/API.

## Tạo lại toàn bộ từ ZIP gốc

```powershell
cd <thu_muc_giai_nen_bundle>
python .\\analyze_step1.py "C:\\duong-dan\\train.zip"
python .\\finalize_step1.py
```

`analyze_step1.py` sẽ ghi lại `sources/`, `schema.sql` là DDL cố định, `schema.json`, `business_rules.json` và `data_dictionary.md` được tạo từ `finalize_step1.py`. Không dùng đáp án khi xây schema/input.

## Kiểm tra SQLite (PowerShell)

```powershell
@'
import sqlite3
c=sqlite3.connect('biz_101.sqlite')
print('sales lines',c.execute('SELECT COUNT(*) FROM sales_lines').fetchone()[0])
print('orders',c.execute('SELECT COUNT(DISTINCT order_id) FROM sales_lines').fetchone()[0])
print('integrity',c.execute('PRAGMA integrity_check').fetchone()[0])
'@ | python -
```

## Cấu trúc

- `sources/`: source dữ liệu và văn bản từ ZIP, chưa sửa
- `inventory.json`: danh sách file SHA-256 và cách dùng
- `data_profile.json`: profiling chính xác và factors quan sát
- `schema.sql`, `schema.json`: SQLite DDL và machine-readable data dictionary
- `data_dictionary.md`: mô tả ngữ nghĩa các cột
- `business_rules.json`: luật có evidence nguồn
- `biz_101.sqlite`: database staging cho SQL coder (dữ liệu)
- `benchmark/questions_biz_101.jsonl`: câu hỏi thật, không có đáp án
- `evaluation_only/answers_biz_101.jsonl`: ground truth, chỉ được load ở evaluation
- `verification.json`: test integrity và đếm dòng
- `STEP1_REPORT.md`: kết luận chuyên môn, rủi ro, bước tiếp theo

**Lưu ý:** Đây là STEP 1, chưa sinh converted questions, coder inputs hay gọi Qwen. Nghiêm cấm đưa `evaluation_only` vào input của Qwen.
'''
(p/'README.md').write_text(readme2,encoding='utf-8')
print('completed', [x.name for x in p.iterdir()])
