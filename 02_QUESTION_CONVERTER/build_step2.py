#!/usr/bin/env python3
"""Reproducible, hand-reviewed DataMate biz_101 question converter (10 real questions).

NO answers.jsonl is ever read by this program; no model or API is called.
Requirements: Python 3.10+, standard library only.
Run: python build_step2.py --step1 ../datamate_step1_biz101 --out .
"""
import argparse
import calendar
import csv
import datetime as dt
import hashlib
import json
import pathlib
import re
import sqlite3
from collections import defaultdict

VERSION = "manual-biz101-step2-v1.0"
VALID_STATUSES = ["Xong", "Đang giao"]

# A non-exhaustive manual interpretation of ten genuine question IDs.  Every
# original question and as_of_date is loaded directly from STEP1 JSONL.
ANNOTATIONS = [
  dict(id="q_0c8f3e07768f", goal="Đếm hóa đơn bán hợp lệ trong quý IV/2025.",
       normalized="Có bao nhiêu hóa đơn bán hợp lệ được đặt từ 01/10/2025 đến hết 31/12/2025?",
       phrase="quy 4/2025", start="2025-10-01",end="2025-12-31",time_type="calendar_quarter",
       metric="valid_order_count", aggregation="count_distinct", measure="order_id",
       group_by=[],top_k=None,sort=[],entity=None,base_unit=None,expected_type="number",rules=["R01","R02","R04","R05","R10","R11"],
       insight="Số đơn là số mã hóa đơn phân biệt, không phải số dòng hàng. Quý 4 dương lịch gồm tháng 10–12."),
  dict(id="q_0cb7c9b93048", goal="Đếm số đơn trong ngày ngay trước as_of_date của câu hỏi.",
       normalized="Có bao nhiêu hóa đơn bán hợp lệ được đặt trong ngày 23/09/2025 (hôm qua so với 24/09/2025)?",
       phrase="hôm qua", start="2025-09-23",end="2025-09-23",time_type="relative_previous_day",
       metric="valid_order_count",aggregation="count_distinct",measure="order_id",group_by=[],top_k=None,sort=[],entity=None,base_unit=None,expected_type="number",rules=["R01","R02","R04","R05","R10","R11"],
       insight="Hôm qua được neo vào as_of_date=2025-09-24, không neo vào ngày máy chạy chương trình."),
  dict(id="q_1cc70c12aa27",goal="Cộng doanh thu bán hợp lệ trong ngày tham chiếu.",
       normalized="Doanh thu bán hàng hợp lệ trong ngày 22/02/2026 (hôm nay theo câu hỏi) là bao nhiêu VND?",
       phrase="Hôm nay",start="2026-02-22",end="2026-02-22",time_type="relative_today",
       metric="net_sales_revenue",aggregation="sum",measure="line_amount_vnd",group_by=[],top_k=None,sort=[],entity=None,base_unit="VND",expected_type="number",rules=["R01","R02","R03","R05","R10","R11"],
       insight="'Bán được bao nhiêu tiền' là doanh thu thành tiền các dòng, không phải số tiền đã thu."),
  dict(id="q_20aa992c0d3f",goal="Tìm ngày có tổng doanh thu lớn nhất trong tháng 5/2026.",
       normalized="Trong tháng 05/2026, ngày nào có tổng doanh thu bán hợp lệ cao nhất? Trả về ngày dương lịch.",
       phrase="thang 5/2026",start="2026-05-01",end="2026-05-31",time_type="calendar_month",
       metric="net_sales_revenue",aggregation="argmax_by_group",measure="line_amount_vnd",group_by=["order_date"],top_k=1,sort=[{"metric":"net_sales_revenue","direction":"desc"}],entity=None,base_unit="VND",expected_type="date",rules=["R01","R02","R03","R05","R10","R11"],
       insight="Phải SUM doanh thu theo từng ngày rồi lấy ngày đứng đầu; không lấy dòng hàng có thành tiền cao nhất."),
  dict(id="q_38e2b6cef714",goal="Tìm mặt hàng có số lượng bán quy đổi lớn nhất trong tháng 6/2026.",
       normalized="Trong tháng 06/2026, mặt hàng nào bán chạy nhất theo tổng số lượng quy về đơn vị cơ bản của đơn hợp lệ?",
       phrase="tháng 6 năm 2026",start="2026-06-01",end="2026-06-30",time_type="calendar_month",
       metric="sold_base_quantity",aggregation="argmax_by_group",measure="base_quantity",group_by=["product_name"],top_k=1,sort=[{"metric":"sold_base_quantity","direction":"desc"},{"metric":"product_name","direction":"asc","purpose":"tie_break"}],entity=None,base_unit="product_base_unit",expected_type="string",rules=["R01","R02","R05","R06","R07","R10","R11"],
       insight="'Bán chạy nhất' không phải doanh thu cao nhất; phải gộp các biến thể tên chỉ khác hoa thường/khoảng trắng trước khi xếp hạng."),
  dict(id="q_62a9a454f35b",goal="Cộng doanh thu các dòng Coca Cola 330ml trong tháng 5/2026.",
       normalized="Doanh thu bán hợp lệ của mặt hàng Coca Cola 330ml (bao gồm biến thể khoảng trắng trong tên) từ 01/05/2026 đến hết 31/05/2026 là bao nhiêu VND?",
       phrase="tháng 5 năm 2026",start="2026-05-01",end="2026-05-31",time_type="calendar_month",
       metric="net_sales_revenue",aggregation="sum",measure="line_amount_vnd",group_by=[],top_k=None,sort=[],entity="Coca Cola 330ml",base_unit="VND",expected_type="number",rules=["R01","R02","R03","R05","R10","R11"],
       insight="Tên hàng trong CSV có biến thể gấp đôi khoảng trắng; cả hai phải được coi là cùng một thực thể."),
  dict(id="q_7c8afb8a81e9",goal="Tính tổng khối lượng nếp bán ra theo kg trong tháng 7/2025.",
       normalized="Trong tháng 07/2025, cửa hàng bán hợp lệ tổng cộng bao nhiêu kg mặt hàng Nếp cái hoa vàng, sau khi quy đổi về kg?",
       phrase="Tháng 7/2025",start="2025-07-01",end="2025-07-31",time_type="calendar_month",
       metric="sold_base_quantity",aggregation="sum",measure="base_quantity",group_by=[],top_k=None,sort=[],entity="Nếp cái hoa vàng",base_unit="kg",expected_type="number",rules=["R01","R02","R05","R07","R08","R10","R11"],
       insight="Số kg dùng đơn vị cơ bản kg của sản phẩm, không dùng số dòng hoặc tổng doanh thu."),
  dict(id="q_fcbf1e1cd8d4",goal="Lấy giá trước chiết khấu tính cho một gói Vinataba tại ngày xác định.",
       normalized="Giá bán ghi trên dòng bán, trước chiết khấu, tính cho một gói Thuốc lá Vinataba vào ngày 28/07/2025 là bao nhiêu VND? Xem cả đơn hủy/trả.",
       phrase="ngày 28/07/2025",start="2025-07-28",end="2025-07-28",time_type="explicit_day",
       metric="unit_selling_price",aggregation="price_observation",measure="sale_price_vnd",group_by=[],top_k=None,sort=[],entity="Thuốc lá Vinataba",base_unit="gói",expected_type="number",rules=["R01","R05","R07","R09","R10","R11"],
       insight="Giá đơn vị trước giảm không phải doanh thu chia lượng bán; không loại đơn hủy/trả. Quy đổi nếu bán theo cây."),
  dict(id="q_c893acce3ef3",goal="Cộng doanh thu bán hợp lệ của toàn cửa hàng tháng 7/2026.",
       normalized="Tổng doanh thu bán hợp lệ của cửa hàng từ 01/07/2026 đến hết 31/07/2026 là bao nhiêu VND?",
       phrase="tháng 7 năm 2026",start="2026-07-01",end="2026-07-31",time_type="calendar_month",
       metric="net_sales_revenue",aggregation="sum",measure="line_amount_vnd",group_by=[],top_k=None,sort=[],entity=None,base_unit="VND",expected_type="number",rules=["R01","R02","R03","R05","R10","R11"],
       insight="Toàn shop: không lọc theo mặt hàng hay khách, phải loại nguyên đơn hủy/trả."),
  dict(id="q_15fd3e0d0363",goal="Cộng doanh thu Vinataba trong tháng 2/2026.",
       normalized="Tổng doanh thu bán hợp lệ của mặt hàng Thuốc lá Vinataba từ 01/02/2026 đến hết 28/02/2026 là bao nhiêu VND?",
       phrase="thang 2/2026",start="2026-02-01",end="2026-02-28",time_type="calendar_month",
       metric="net_sales_revenue",aggregation="sum",measure="line_amount_vnd",group_by=[],top_k=None,sort=[],entity="Thuốc lá Vinataba",base_unit="VND",expected_type="number",rules=["R01","R02","R03","R05","R10","R11"],
       insight="'Thu về bao nhiêu tiền' mặc định là doanh thu, không phải tiền đã thanh toán; tháng 02/2026 có 28 ngày."),
]

RULE_EVIDENCE = {
 "R01":"train/rulebook.md: line 5", "R02":"train/rulebook.md: lines 7-15",
 "R03":"train/rulebook.md: lines 11-15", "R04":"train/rulebook.md: line 14",
 "R05":"train/rulebook.md: lines 22-35", "R06":"train/rulebook.md: lines 38-46, 135-136",
 "R07":"train/rulebook.md: lines 43-44, 139-142; train/data/biz_101/README.md: Quy ước",
 "R08":"train/rulebook.md: line 44", "R09":"train/rulebook.md: line 70",
 "R10":"train/rulebook.md: line 111", "R11":"train/rulebook.md: lines 97-101",
}

def norm_name(x):
    return " ".join(x.strip().casefold().split())

def read_jsonl(p):
    with p.open(encoding="utf-8-sig") as f:
        return [json.loads(ln) for ln in f if ln.strip()]

def save_json(p,obj):
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def build(step1, out):
    path=step1/"benchmark/questions_biz_101.jsonl"
    src=read_jsonl(path)
    srcmap={q["id"]:q for q in src}
    rules_path=step1/"business_rules.json"
    rulemap={r["id"]:r for r in json.loads(rules_path.read_text(encoding="utf-8"))["rules"]}
    schema_path=step1/"schema.json"
    schema=json.loads(schema_path.read_text(encoding="utf-8"))
    allowed_columns={c["name"] for tab in schema["tables"] if tab["name"]=="sales_lines" for c in tab["columns"]}
    conn=sqlite3.connect(f"file:{(step1/'biz_101.sqlite').resolve().as_posix()}?mode=ro",uri=True)
    conn.execute('PRAGMA query_only=ON')
    distinct_names=[row[0] for row in conn.execute("SELECT DISTINCT product_name FROM sales_lines")]
    name_groups=defaultdict(list)
    for name in distinct_names: name_groups[norm_name(name)].append(name)
    data_min,data_max=conn.execute("SELECT MIN(order_date),MAX(order_date) FROM sales_lines").fetchone()
    output=[]; audit=[]
    for s in ANNOTATIONS:
        q=srcmap.get(s["id"])
        if q is None: raise ValueError(f"Missing original question ID: {s['id']}")
        if q["business_id"]!="biz_101": raise ValueError("Unexpected business ID")
        reference=q["as_of_date"]
        sd=dt.date.fromisoformat(s["start"]);ed=dt.date.fromisoformat(s["end"]);anchor=dt.date.fromisoformat(reference)
        assert sd <= ed <= anchor, (s['id'],sd,ed,anchor)
        if s["time_type"]=="relative_previous_day":assert sd==ed==anchor-dt.timedelta(days=1)
        if s["time_type"]=="relative_today":assert sd==ed==anchor
        if s["time_type"]=="calendar_month":
            assert sd.day==1 and ed.day==calendar.monthrange(sd.year,sd.month)[1] and sd.month==ed.month
        if s["time_type"]=="calendar_quarter": assert (sd.month,sd.day,ed.month,ed.day)==(10,1,12,31)
        if not (data_min <= s["end"] and data_max >= s["start"]): raise ValueError("Requested period outside data coverage")
        if s["measure"] not in allowed_columns or any(c not in allowed_columns for c in s["group_by"]):
            raise ValueError("Unknown SQLite column in converter")
        uses_sales_filter=s["metric"]!="unit_selling_price"
        filters=[{"field":"order_date","operator":"between_inclusive","value":[s["start"],s["end"]],"source":"question+as_of_date"}]
        if uses_sales_filter:
            filters.append({"field":"order_status","operator":"in","value":VALID_STATUSES,"source_rule":"R02"})
        aliases=[]
        if s["entity"]:
            aliases=sorted(name_groups.get(norm_name(s["entity"]),[]))
            if not aliases: raise ValueError(f"Entity not in actual business data: {s['entity']}")
            filters.append({"field":"product_name","operator":"in","value":aliases,"source":"train/data/biz_101/ban_hang.csv + train/rulebook.md §8"})
        if s["base_unit"]=="kg":
            unit_rows=conn.execute("SELECT DISTINCT unit FROM sales_lines WHERE product_name IN ("+','.join('?'*len(aliases))+")",aliases).fetchall()
            if any(u[0]!="kg" for u in unit_rows): raise ValueError("Expected kg-only source: recheck unit normalization")
        extra={}
        if s["metric"]=="unit_selling_price":
            # Source README explicitly states one 'cây' Vinataba = ten 'gói'.
            unit_values=conn.execute("SELECT DISTINCT unit FROM sales_lines WHERE product_name IN ("+','.join('?'*len(aliases))+")",aliases).fetchall()
            if not {"gói","cây"}.issuperset({u[0] for u in unit_values}): raise ValueError("Unexpected Vinataba unit")
            extra={"requested_base_unit":"gói", "value_before_line_discount":True,
                   "include_canceled_and_returned_orders":True,
                   "unit_factor_definition":"base_quantity / quantity",
                   "price_per_base_unit_definition":"sale_price_vnd / unit_factor",
                   "source":"train/rulebook.md §5; train/data/biz_101/README.md: Thuốc lá Vinataba"}
        record={
          "converter_version":VERSION,
          "question_id":q["id"],"business_id":q["business_id"],
          "original_question":q["question"],"as_of_date":reference,
          "semantic_analysis":{"user_goal":s["goal"],"interpretation":s["insight"],
                               "semantic_type":s["aggregation"],"question_phrase":s["phrase"]},
          "normalized_question":s["normalized"],
          "intent":{"metric":s["metric"],"aggregation":s["aggregation"],"measure_column":s["measure"],
                    "group_by":s["group_by"],"filters":filters,"sort":s["sort"],"top_k":s["top_k"],
                    "entity":{"kind":"product","canonical_name":s["entity"],"observed_aliases":aliases} if s["entity"] else None,
                    "requested_unit":s["base_unit"],"expected_answer_type":s["expected_type"],
                    "needs_join":False,"required_relations":["sales_lines"],
                    "identity_policy":{"normalize_case":True,"collapse_whitespace":True,
                                        "source":"train/rulebook.md §8"} if (s["entity"] or s["group_by"]==["product_name"]) else None,
                    "price_semantics":extra if extra else None},
          "temporal_constraints":{"original_expression":s["phrase"],"normalization_kind":s["time_type"],
                                  "reference_date":reference,"start_date":s["start"],"end_date":s["end"],
                                  "inclusive_start":True,"inclusive_end":True,
                                  "timezone":"date-only (business-local unspecified)",
                                  "restrict_to_as_of_date":True},
          "required_business_rules":[{"id":rid,"source":RULE_EVIDENCE[rid],"applies":"conversion context"} for rid in s["rules"]],
          "ambiguities":[],
          "conditional_risks": (["If several equal highest-revenue dates occur, rulebook does not explicitly specify day-tie ordering; do not silently choose one."]
                                if s["id"]=="q_20aa992c0d3f" else
                                ["If multiple different historical per-pack prices are observed on the same day, return ambiguity rather than averaging without a source rule."]
                                if s["id"]=="q_fcbf1e1cd8d4" else []),
          "status":"ready",
          "provenance":{"question_file":"train/questions.jsonl (filtered from STEP1 benchmark/questions_biz_101.jsonl)",
                        "business_readme":"train/data/biz_101/README.md","rulebook":"train/rulebook.md",
                        "schema_file":"STEP1/schema.json","manual_annotation":VERSION}
        }
        output.append(record)
        # Audits are separate from converter records and never provide reference answers.
        probe="SELECT COUNT(*) FROM sales_lines WHERE order_date BETWEEN ? AND ?"
        params=[s["start"],s["end"]]
        if s["entity"]:
            probe += " AND product_name IN ("+','.join('?'*len(aliases))+")"
            params+=aliases
        exists=conn.execute(probe,params).fetchone()[0] > 0
        price_price_levels=None
        if s["metric"]=="unit_selling_price":
            vals=conn.execute("SELECT DISTINCT 1.0*sale_price_vnd*quantity/base_quantity FROM sales_lines WHERE order_date BETWEEN ? AND ? AND product_name IN ("+','.join('?'*len(aliases))+")",params).fetchall()
            price_price_levels=len(vals)
        audit.append({"question_id":s["id"],"source_question_found":True,"source_question_unchanged":True,
                      "business_id_matches":True,"time_range_valid":True,"as_of_causality_valid":True,
                      "fields_exist_in_schema":True,"required_rules_exist":all(x in rulemap for x in s["rules"]),
                      "source_period_overlap":True,"rows_for_requested_scope_exist":exists,
                      "product_aliases_verified":bool(aliases) if s["entity"] else "not_applicable",
                      "distinct_price_levels_for_requested_day":price_price_levels,
                      "note":"Scope probe validates data existence only; NO answer calculation or ground-truth lookup."})
    conn.close()
    out.mkdir(parents=True,exist_ok=True)
    out_path=out/"converted_questions.jsonl"
    with out_path.open("w",encoding="utf-8") as f:
        for rec in output: f.write(json.dumps(rec,ensure_ascii=False)+"\n")
    mapping=out/"converter_mapping.csv"
    with mapping.open("w",newline="",encoding="utf-8-sig") as f:
        fields=["question_id","original_question","as_of_date","normalized_question","metric","aggregation","group_by","product","time_start","time_end","required_rules","ambiguities","status"]
        w=csv.DictWriter(f,fields);w.writeheader()
        for r in output:
            i=r["intent"]; t=r["temporal_constraints"]
            w.writerow({"question_id":r["question_id"],"original_question":r["original_question"],
                        "as_of_date":r["as_of_date"],"normalized_question":r["normalized_question"],
                        "metric":i["metric"],"aggregation":i["aggregation"],"group_by":'|'.join(i["group_by"]),
                        "product":(i["entity"] or {}).get("canonical_name", ""),
                        "time_start":t["start_date"],"time_end":t["end_date"],
                        "required_rules":'|'.join(x["id"] for x in r["required_business_rules"]),
                        "ambiguities":json.dumps(r["ambiguities"],ensure_ascii=False),"status":r["status"]})
    save_json(out/"verification.json",{
      "status":"passed" if all(row["rows_for_requested_scope_exist"] and row["required_rules_exist"] for row in audit) else "needs_review",
      "records":len(output),"input_questions_total":len(src),"original_question_file_sha256":sha(path),
      "schema_sha256":sha(schema_path),"business_rules_sha256":sha(rules_path),
      "sqlite_scope_checks_do_not_compute_answers":True,
      "ground_truth_used":False,"model_or_external_api_used":False,
      "note":"A passed converter validation is NOT semantic answer accuracy or model accuracy.",
      "audit":audit})
    return output,audit

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--step1',type=pathlib.Path,default=pathlib.Path('../datamate_step1_biz101'))
    p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('.'))
    a=p.parse_args()
    records,checks=build(a.step1.resolve(),a.out.resolve())
    print(f'Created {len(records)} genuine question conversion records in {a.out.resolve()}')
    print('Scope checks:',sum(x['rows_for_requested_scope_exist'] for x in checks),'of',len(checks),'have supporting source rows')
