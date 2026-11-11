#!/usr/bin/env python3
"""Reproducible source-grounded STEP 1 inventory and SQLite staging for DataMate biz_101.
Usage: python analyze_step1.py /path/to/train.zip
"""
from __future__ import annotations
import csv, hashlib, io, json, re, sqlite3, sys, zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
NAMES = {
 'readme':'train/data/biz_101/README.md', 'data':'train/data/biz_101/ban_hang.csv',
 'rulebook':'train/rulebook.md','calendar':'train/calendar.csv',
 'questions':'train/questions.jsonl'
}
MAP = {'Giá bán':'sale_price_vnd','Kết quả':'order_status','Nội dung':'product_name',
 'Ngày tháng':'order_date','Đơn vị (tính)':'unit','so_luong':'quantity',
 'Thanh tien':'line_amount_vnd','Quy ra ĐV lẻ':'base_quantity',
 'Mã hóa đơn':'order_id','Đối tác':'customer_name'}
STATUS = ['Xong','Đã hủy','Đổi trả','Đang giao']
def dump(path, value):
 path.parent.mkdir(parents=True, exist_ok=True)
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
def csv_rows(b):
 return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig')), strict=True))
def parse_money(v):
 s=v.replace(',','').strip()
 if not re.fullmatch(r'-?\d+',s): raise ValueError(f'Non-integral money: {v!r}')
 return int(s)
def parse_date(v):
 m=re.fullmatch(r'\s*(\d{1,2})\s+thg\s+(\d{1,2})\s+(\d{4})\s*',v)
 if not m:raise ValueError(f'Unknown date format: {v}')
 return date(int(m[3]),int(m[2]),int(m[1])).isoformat()
def main(zip_path):
 zip_path=Path(zip_path)
 with zipfile.ZipFile(zip_path) as z:
  names=set(z.namelist()); assert all(v in names for v in NAMES.values()),'Missing file(s)'
  assert z.testzip() is None,'Invalid CRC'
  src={k:z.read(v) for k,v in NAMES.items()}
  others=[(i.filename,i.file_size) for i in z.infolist() if i.filename.startswith('train/data/biz_101/') and not i.is_dir()]
 sources=ROOT/'sources';sources.mkdir(exist_ok=True)
 for k,b in src.items():
  ext=Path(NAMES[k]).suffix
  (sources/(k+ext)).write_bytes(b)
 rows=csv_rows(src['data']);calendar=csv_rows(src['calendar']);n=len(rows)
 qs=[json.loads(s) for s in src['questions'].decode('utf-8-sig').splitlines() if s.strip()]
 bqs=[q for q in qs if q['business_id']=='biz_101']
 assert n==56501 and len(bqs)==40,(n,len(bqs))
 cols=list(rows[0]);assert list(MAP)==cols
 inventory=[]
 for k,p in NAMES.items():
  b=src[k];inventory.append({'logical_name':k,'zip_member':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'rows': {'data':n,'questions':len(qs),'calendar':len(calendar)}.get(k),'model_prompt_usage': 'source for rules/schema/context' if k in ('readme','rulebook','calendar','data') else ('question text only, filtered business' if k=='questions' else 'unknown source category')})
 dump(ROOT/'inventory.json',{'zip_file':str(zip_path),'zip_sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),'biz_101_files':others,'archive_members':inventory,'questions_biz_101':len(bqs)})
 sums={k:{'null':sum(x[k] is None or x[k]=='' for x in rows),'unique':len({x[k] for x in rows})} for k in cols}
 for k in cols:
  cnt=Counter(x[k] for x in rows)
  sums[k]['examples']=[{'value':a,'count':b} for a,b in cnt.most_common(8)]
  sums[k]['sqlite_column']=MAP[k]
  sums[k]['type']='INTEGER' if k in ['Giá bán','so_luong','Thanh tien','Quy ra ĐV lẻ'] else ('TEXT ISO date parsed' if k=='Ngày tháng' else 'TEXT')
 norm=[];bad=[]
 for i,r in enumerate(rows,2):
  try:
   d={MAP[k]:(parse_money(r[k]) if k in ['Giá bán','so_luong','Thanh tien','Quy ra ĐV lẻ'] else parse_date(r[k]) if k=='Ngày tháng' else r[k]) for k in cols}
   d['source_csv_line']=i;norm.append(d)
  except ValueError as ex:bad.append({'line':i,'error':str(ex)})
 order_groups=defaultdict(list)
 for d in norm:order_groups[d['order_id']].append(d)
 conflicting={k:{'statuses':sorted({r['order_status'] for r in v}),'dates':sorted({r['order_date'] for r in v}),'customers':sorted({r['customer_name'] for r in v})} for k,v in order_groups.items() if any(len({r[c] for r in v})>1 for c in ('order_status','order_date','customer_name'))}
 sigs=Counter(tuple(r[k] for k in MAP.values()) for r in norm)
 dup_count=sum(v-1 for v in sigs.values() if v>1)
 flagged=[];seen=set()
 for r in norm:
  signature=tuple(r[k] for k in MAP.values());is_dup=int(signature in seen);seen.add(signature)
  r['is_duplicate_export']=is_dup
  if r['order_status'] not in STATUS:flagged.append({'line':r['source_csv_line'],'type':'status','value':r['order_status']})
 dates=sorted({r['order_date'] for r in norm});statuses=Counter(r['order_status'] for r in norm)
 status_orders=Counter(next(iter({r['order_status'] for r in group})) for group in order_groups.values() if len({r['order_status'] for r in group})==1)
 products=Counter(r['product_name'] for r in norm)
 qty_errors=[r['source_csv_line'] for r in norm if r['quantity']<=0 or r['base_quantity']<=0 or r['sale_price_vnd']<0 or r['line_amount_vnd']<0]
 amount_diff=[r['source_csv_line'] for r in norm if r['line_amount_vnd']>r['sale_price_vnd']*r['quantity']]
 pair_factor=defaultdict(set)
 for r in norm:
  if r['quantity']:pair_factor[(r['product_name'],r['unit'])].add(r['base_quantity']/r['quantity'])
 varying=[{'product_name':p,'unit':u,'factors':sorted(fs)} for (p,u),fs in pair_factor.items() if len(fs)>1]
 product_unit_summary=[{'product_name':p,'unit':u,'observed_factors':sorted(fs)} for (p,u),fs in sorted(pair_factor.items())]
 dump(ROOT/'data_profile.json',{'rows':n,'cols':len(cols),'column_profiles':sums,'date_min':dates[0],'date_max':dates[-1],'unique_dates':len(dates),'distinct_orders':len(order_groups),'distinct_products':len(products),'distinct_customers_including_walk_in':len(set(r['customer_name'] for r in norm)),'statuses_by_line':statuses,'statuses_by_order_consistent_only':status_orders,'orders_with_inconsistent_attributes_count':len(conflicting),'orders_with_inconsistent_attributes_sample':dict(list(conflicting.items())[:20]),'exact_duplicate_extra_lines':dup_count,'duplicate_rule':'Identical all columns AND same order -> count once, per rulebook §8','money_greater_than_qty_times_unit_price_count':len(amount_diff),'money_greater_than_qty_times_unit_price_sample':amount_diff[:20],'invalid_or_negative_qty_price_amount_count':len(qty_errors),'invalid_or_negative_qty_price_amount_sample':qty_errors[:20],'parse_errors':bad[:30],'unexpected_status':flagged[:30],'products':sorted(products),'observed_unit_factors':product_unit_summary,'varying_unit_factors':varying,'calendar_date_range':[calendar[0]['date'],calendar[-1]['date']],'calendar_rows':len(calendar),'questions_biz_101':len(bqs)})
 # Save only source questions; reference answers are NEVER read, stored or packaged.
 bench=ROOT/'benchmark';bench.mkdir(exist_ok=True)
 with (bench/'questions_biz_101.jsonl').open('w',encoding='utf-8') as f:
  for q in bqs:f.write(json.dumps(q,ensure_ascii=False)+'\n')
 # SQLite is an exact-staging transform: preserve source line, values, status; no unilateral business deductions.
 db=ROOT/'biz_101.sqlite';db.unlink(missing_ok=True)
 con=sqlite3.connect(db)
 sql=(ROOT/'schema.sql').read_text(encoding='utf-8');con.executescript(sql)
 inserts=['source_csv_line']+list(MAP.values())+['is_duplicate_export']
 stmt=f"INSERT INTO sales_lines_raw ({','.join(inserts)}) VALUES ({','.join('?' for _ in inserts)})"
 con.executemany(stmt,([r[k] for k in inserts] for r in norm))
 con.executemany('INSERT INTO calendar(date,weekday,lunar_day,lunar_month,lunar_year,lunar_leap,holiday) VALUES(?,?,?,?,?,?,?)',[(r['date'],int(r['weekday']),int(r['lunar_day']),int(r['lunar_month']),int(r['lunar_year']),int(r['lunar_leap'].lower()=='true'),r['holiday']) for r in calendar]);con.commit()
 checks={'raw_rows_sqlite':con.execute('select count(*) from sales_lines_raw').fetchone()[0],'dedup_rows_sqlite':con.execute('select count(*) from sales_lines').fetchone()[0],'distinct_order_ids_sqlite':con.execute('select count(distinct order_id) from sales_lines').fetchone()[0],'sqlite_integrity':con.execute('pragma integrity_check').fetchone()[0]}
 con.close();dump(ROOT/'verification.json',checks)
 print(json.dumps({'rows':n,'questions':len(bqs),'date_range':[dates[0],dates[-1]],'statuses':statuses,'duplicates':dup_count,'orders':len(order_groups),'inconsistent_orders':len(conflicting),'bad_parse':len(bad),'verification':checks},ensure_ascii=False,indent=2))
if __name__=='__main__':
 if len(sys.argv)!=2:sys.exit('Usage: python analyze_step1.py train.zip')
 main(sys.argv[1])
