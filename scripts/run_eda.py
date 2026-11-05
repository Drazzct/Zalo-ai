"""Comprehensive Exploratory Data Analysis (EDA) script for Zalo AI DataMate.

Analyzes train and public_test datasets, inspects business files (csv, xlsx,
sqlite),
reads README notes, parses question patterns, and analyzes answer distributions.
"""

from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import sqlite3
import openpyxl
import pandas as pd


def analyze_csv(file_path: Path) -> dict:
  """Analyze CSV file headers, row count, and missing values."""
  try:
    df = pd.read_csv(file_path, nrows=5)
    total_rows = sum(1 for _ in open(file_path, encoding='utf-8', errors='ignore')) - 1
    return {
        'type': 'csv',
        'rows': total_rows,
        'columns': list(df.columns),
        'sample_row': df.iloc[0].to_dict() if len(df) > 0 else {},
    }
  except Exception as e:
    return {'type': 'csv', 'error': str(e)}


def analyze_xlsx(file_path: Path) -> dict:
  """Analyze Excel file sheets, sheet row count, columns, and empty cell pattern."""
  try:
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    sheets_info = {}
    for sheet_name in wb.sheetnames:
      ws = wb[sheet_name]
      rows = list(ws.iter_rows(values_only=True))
      if rows:
        header = [
            str(c) if c is not None else f'col_{i}'
            for i, c in enumerate(rows[0])
        ]
        sample = (
            [str(v) if v is not None else '' for v in rows[1]]
            if len(rows) > 1
            else []
        )
        sheets_info[sheet_name] = {
            'rows': len(rows) - 1,
            'columns': header,
            'sample_row': sample,
        }
      else:
        sheets_info[sheet_name] = {'rows': 0, 'columns': []}
    wb.close()
    return {'type': 'xlsx', 'sheets': sheets_info}
  except Exception as e:
    return {'type': 'xlsx', 'error': str(e)}


def analyze_sqlite(file_path: Path) -> dict:
  """Analyze SQLite tables and row counts."""
  try:
    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    table_info = {}
    for t in tables:
      cursor.execute(f'SELECT COUNT(*) FROM "{t}"')
      cnt = cursor.fetchone()[0]
      cursor.execute(f'PRAGMA table_info("{t}")')
      cols = [col[1] for col in cursor.fetchall()]
      table_info[t] = {'rows': cnt, 'columns': cols}
    conn.close()
    return {'type': 'sqlite', 'tables': table_info}
  except Exception as e:
    return {'type': 'sqlite', 'error': str(e)}


def analyze_businesses(split_dir: Path) -> dict:
  """Analyze all businesses inside split_dir/data."""
  data_dir = split_dir / 'data'
  if not data_dir.exists():
    return {}

  businesses = {}
  for biz_path in sorted(data_dir.iterdir()):
    if not biz_path.is_dir():
      continue
    biz_id = biz_path.name
    files_info = {}
    readme_content = ''
    readme_sections = []

    for file in sorted(biz_path.iterdir()):
      if file.name == 'README.md':
        try:
          readme_content = file.read_text(encoding='utf-8')
          readme_sections = [
              line.strip()
              for line in readme_content.splitlines()
              if line.strip().startswith('#')
          ]
        except Exception:
          pass
      elif file.suffix.lower() == '.csv':
        files_info[file.name] = analyze_csv(file)
      elif file.suffix.lower() == '.xlsx':
        files_info[file.name] = analyze_xlsx(file)
      elif file.suffix.lower() == '.sqlite':
        files_info[file.name] = analyze_sqlite(file)

    businesses[biz_id] = {
        'files_count': len(files_info),
        'file_names': list(files_info.keys()),
        'files_detail': files_info,
        'readme_length': len(readme_content),
        'readme_sections': readme_sections,
    }
  return businesses


def analyze_questions(file_path: Path) -> dict:
  """Analyze questions dataset."""
  if not file_path.exists():
    return {}

  records = []
  with open(file_path, encoding='utf-8') as f:
    for line in f:
      if line.strip():
        records.append(json.loads(line))

  total = len(records)
  biz_counter = Counter(r['business_id'] for r in records)
  as_of_dates = [r['as_of_date'] for r in records if 'as_of_date' in r]

  # Keyword pattern check
  keywords = [
      'doanh thu',
      'dthu',
      'tiền',
      'bán chạy',
      'huỷ',
      'hủy',
      'trả hàng',
      'nợ',
      'công nợ',
      'lãi',
      'lợi nhuận',
      'tồn kho',
      'hết hàng',
      'nhập',
      'giá nhập',
      'giá bán',
      'tăng giá',
      'Tết',
      'ca sáng',
      'ca chiều',
      'hôm nay',
      'hôm qua',
      'tháng này',
      'tuần này',
      'tuần trước',
      'size',
      'thuốc',
      'kê đơn',
      'hoạt chất',
      'bảo hành',
      'biển số',
      'trả góp',
  ]
  kw_counter = defaultdict(int)
  for r in records:
    q_lower = r['question'].lower()
    for kw in keywords:
      if kw.lower() in q_lower:
        kw_counter[kw] += 1

  return {
      'total': total,
      'businesses_involved': len(biz_counter),
      'min_as_of_date': min(as_of_dates) if as_of_dates else None,
      'max_as_of_date': max(as_of_dates) if as_of_dates else None,
      'keyword_frequencies': dict(
          sorted(kw_counter.items(), key=lambda x: x[1], reverse=True)
      ),
  }


def analyze_answers(file_path: Path) -> dict:
  """Analyze ground truth answers dataset."""
  if not file_path.exists():
    return {}

  records = []
  with open(file_path, encoding='utf-8') as f:
    for line in f:
      if line.strip():
        records.append(json.loads(line))

  total = len(records)
  type_counter = Counter(r.get('type') for r in records)
  alias_count = sum(1 for r in records if r.get('alias'))
  unanswerable_reasons = [
      r.get('reason') for r in records if r.get('type') == 'unanswerable'
  ]

  return {
      'total': total,
      'types_distribution': dict(type_counter),
      'questions_with_alias': alias_count,
      'sample_unanswerable_reasons': unanswerable_reasons[:10],
  }


def main():
  root = Path('.')
  report = {}

  print('=' * 60)
  print('EXPLORATORY DATA ANALYSIS (EDA) - ZALO AI DATAMATE')
  print('=' * 60)

  # 1. Train businesses
  print('\n[1/4] Analyzing train businesses...')
  train_biz = analyze_businesses(root / 'train')
  report['train_businesses'] = train_biz
  print(f'-> Analyzed {len(train_biz)} train businesses.')

  # 2. Public test businesses
  print('\n[2/4] Analyzing public_test businesses...')
  test_biz = analyze_businesses(root / 'public_test')
  report['public_test_businesses'] = test_biz
  print(f'-> Analyzed {len(test_biz)} public_test businesses.')

  # 3. Questions
  print('\n[3/4] Analyzing questions...')
  train_q = analyze_questions(root / 'train' / 'questions.jsonl')
  test_q = analyze_questions(root / 'public_test' / 'questions.jsonl')
  report['train_questions'] = train_q
  report['public_test_questions'] = test_q
  print(f"-> Train questions: {train_q.get('total')}")
  print(f"-> Public test questions: {test_q.get('total')}")

  # 4. Answers
  print('\n[4/4] Analyzing train answers...')
  train_a = analyze_answers(root / 'train' / 'answers.jsonl')
  report['train_answers'] = train_a
  print(f"-> Train answers breakdown: {train_a.get('types_distribution')}")

  # Save report
  out_dir = root / 'reports'
  out_dir.mkdir(exist_ok=True)
  out_file = out_dir / 'eda_summary.json'
  with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

  print(f'\n[SUCCESS] EDA report saved to {out_file.resolve()}')
  print('=' * 60)


if __name__ == '__main__':
  main()

