"""Data Ingestor Module for Zalo AI DataMate.

Loads heterogeneous files (.csv, .xlsx, .sqlite) into an analytical DuckDB
database.
Handles header offsets, forward-filling order metadata, Vietnamese date formats,
number cleaning with thousand separators, multi-sheet union, and deduplication.
"""

from datetime import date, datetime, timedelta
import math
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional, Set, Tuple
import unicodedata
import duckdb
import openpyxl
import pandas as pd


def remove_accents(input_str: str) -> str:
  """Remove Vietnamese accents and convert to ASCII."""
  if not input_str:
    return ''
  s1 = unicodedata.normalize('NFD', input_str)
  s2 = ''.join(c for c in s1 if unicodedata.category(c) != 'Mn')
  s2 = s2.replace('đ', 'd').replace('Đ', 'D')
  return s2


def to_snake_case(name: str) -> str:
  """Convert column/table name to clean snake_case identifier."""
  ascii_name = remove_accents(str(name)).strip()
  # Insert underscore between camelCase boundaries (e.g. DonHang -> Don_Hang)
  s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', ascii_name)
  # Replace non-alphanumeric with underscore
  clean = re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_').lower()
  if not clean:
    clean = 'col'
  if clean[0].isdigit():
    clean = 'c_' + clean
  return clean


def parse_clean_number(val: Any) -> Optional[float]:
  """Clean string number with commas, dots, currency, percentage symbols."""
  if val is None or (isinstance(val, float) and math.isnan(val)):
    return None
  if isinstance(val, (int, float)):
    return float(val)

  s = str(val).strip()
  if not s or s.lower() in ('none', 'null', 'nan', '-', ''):
    return None

  # Remove currency and units
  s = re.sub(r'[đĐkKmM%]', '', s).strip()

  # Check comma/dot pattern: e.g. "560,000" or "1.500.000"
  if ',' in s and '.' in s:
    if s.rfind(',') > s.rfind('.'):
      # European style: 1.500,50
      s = s.replace('.', '').replace(',', '.')
    else:
      # US style: 1,500.50
      s = s.replace(',', '')
  elif ',' in s:
    parts = s.split(',')
    # If all parts after first have 3 digits -> thousand separator
    if all(len(p) == 3 for p in parts[1:]):
      s = s.replace(',', '')
    else:
      s = s.replace(',', '.')
  elif '.' in s:
    parts = s.split('.')
    if all(len(p) == 3 for p in parts[1:]):
      s = s.replace('.', '')

  try:
    return float(s)
  except ValueError:
    return None


def parse_vietnamese_date(val: Any, default_year: Optional[int] = None) -> Optional[str]:
  """Parse various Vietnamese date formats to YYYY-MM-DD or YYYY-MM-DD HH:MM:SS."""
  if val is None or (isinstance(val, float) and math.isnan(val)):
    return None

  if isinstance(val, (datetime, pd.Timestamp)):
    return val.strftime('%Y-%m-%d %H:%M:%S') if val.hour or val.minute or val.second else val.strftime('%Y-%m-%d')
  if isinstance(val, date):
    return val.strftime('%Y-%m-%d')

  # If Excel serial date number
  if isinstance(val, (int, float)) and 30000 <= val <= 60000:
    try:
      converted = datetime(1899, 12, 30) + timedelta(days=val)
      return converted.strftime('%Y-%m-%d')
    except Exception:
      pass

  s = str(val).strip()
  if not s or s.lower() in ('none', 'null', 'nan'):
    return None

  # Format: "1 thg 6 2025" or "15 thg 12 2025"
  thg_match = re.search(r'(\d{1,2})\s+thg\s+(\d{1,2})\s+(\d{4})', s, re.IGNORECASE)
  if thg_match:
    d, m, y = map(int, thg_match.groups())
    return f'{y:04d}-{m:02d}-{d:02d}'

  # Format: DD/MM/YYYY or DD-MM-YYYY (with optional HH:MM:SS)
  slash_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?:\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?', s)
  if slash_match:
    d, m, y, h, mi, sec = slash_match.groups()
    if h is not None:
      sec_str = f':{int(sec):02d}' if sec is not None else ':00'
      return f'{int(y):04d}-{int(m):02d}-{int(d):02d} {int(h):02d}:{int(mi):02d}{sec_str}'
    return f'{int(y):04d}-{int(m):02d}-{int(d):02d}'

  # Format: YYYY-MM-DD (with optional HH:MM:SS)
  iso_match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})(?:\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?', s)
  if iso_match:
    y, m, d, h, mi, sec = iso_match.groups()
    if h is not None:
      sec_str = f':{int(sec):02d}' if sec is not None else ':00'
      return f'{int(y):04d}-{int(m):02d}-{int(d):02d} {int(h):02d}:{int(mi):02d}{sec_str}'
    return f'{int(y):04d}-{int(m):02d}-{int(d):02d}'

  # Format missing year: DD/MM (use default_year if provided)
  no_year_match = re.search(r'^(\d{1,2})[/-](\d{1,2})$', s)
  if no_year_match and default_year:
    d, m = map(int, no_year_match.groups())
    return f'{default_year:04d}-{m:02d}-{d:02d}'

  # Check if already ISO format YYYY-MM-DD
  if re.match(r'^\d{4}-\d{2}-\d{2}', s):
    return s

  # Not a recognized date format
  return None


class DataIngestor:
  """Loads and cleans business data into DuckDB."""

  ORDER_GROUP_KEYS = ['ma_don_hang', 'ma_don', 'ma_hoa_don', 'so_hoa_don', 'ma_phieu']
  ORDER_METADATA_COLS = [
      'ngay_dat_hang', 'ngay_ban', 'ngay_dat', 'ngay_thang', 'ngay',
      'trang_thai_don_hang', 'trang_thai_don', 'trang_thai', 'ket_qua',
      'ten_khach_hang', 'ten_khach', 'doi_tac', 'khach_hang', 'ma_khach_hang', 'ma_khach',
      'ghi_chu', 'nhan_vien'
  ]

  def __init__(self, db_path: str = ':memory:'):
    self.con = duckdb.connect(db_path)
    # Store mappings: {table_name: {clean_col: orig_col}}
    self.column_mappings: Dict[str, Dict[str, str]] = {}
    self.table_sources: Dict[str, str] = {}

  def load_calendar(self, calendar_csv: Path) -> None:
    """Load calendar.csv into table 'calendar'."""
    if not calendar_csv.exists():
      return
    df = pd.read_csv(calendar_csv)
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    self.con.register('calendar_df', df)
    self.con.execute('CREATE OR REPLACE TABLE calendar AS SELECT * FROM calendar_df')
    self.con.unregister('calendar_df')

  def _detect_header_row(self, rows: List[Tuple]) -> int:
    """Detect true header row index from first 10 rows."""
    best_idx = 0
    max_score = -1

    header_keywords = [
        'ma', 'ten', 'ngay', 'so_luong', 'gia', 'tien', 'don_vi', 'trang_thai',
        'hang', 'san_pham', 'khach', 'doi_tac', 'nhap', 'lo', 'sku'
    ]

    for idx, row in enumerate(rows[:10]):
      if not row:
        continue
      non_empty = [str(c).strip() for c in row if c is not None and str(c).strip()]
      if len(non_empty) < 2:
        continue

      score = len(non_empty)
      for c in non_empty:
        c_clean = to_snake_case(c)
        if any(kw in c_clean for kw in header_keywords):
          score += 3
      if score > max_score:
        max_score = score
        best_idx = idx

    return best_idx

  def _forward_fill_order_group(self, df: pd.DataFrame, clean_cols: List[str]) -> pd.DataFrame:
    """Forward-fill order metadata within the same order group according to Rule 8."""
    # Find which column serves as order key
    key_col = next((c for c in clean_cols if c in self.ORDER_GROUP_KEYS), None)
    if not key_col or key_col not in df.columns:
      return df

    # Find which metadata columns exist in df
    meta_cols_to_fill = [c for c in clean_cols if c in self.ORDER_METADATA_COLS and c in df.columns]
    if not meta_cols_to_fill:
      return df

    # If key_col has nulls, forward fill key_col first (subsequent lines of the order)
    df[key_col] = df[key_col].ffill()

    # Forward fill metadata columns grouped by order key
    for col in meta_cols_to_fill:
      df[col] = df.groupby(key_col)[col].ffill()

    return df

  def _clean_dataframe(
      self,
      df: pd.DataFrame,
      sheet_name: str = '',
      file_name: str = ''
  ) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Clean column names, parse dates, numbers, forward-fill, and deduplicate."""
    orig_cols = list(df.columns)
    clean_cols = []
    seen = {}
    col_map = {}

    for c in orig_cols:
      sc = to_snake_case(c)
      if sc in seen:
        seen[sc] += 1
        sc = f'{sc}_{seen[sc]}'
      else:
        seen[sc] = 0
      clean_cols.append(sc)
      col_map[sc] = str(c)

    df.columns = clean_cols

    # Filter out report summary/total/footnote rows (e.g. "Tổng tháng", "Tổng cộng", "Cộng", "Ghi chú:")
    def is_footer_or_summary(row):
      non_empty = [c for c in row if pd.notna(c) and str(c).strip()]
      if len(non_empty) <= max(2, len(row) // 2):
        for c in non_empty:
          c_str = str(c).strip().lower()
          if re.search(r'^\s*(?:tổng|tong|cộng|cong|ghi\s*chú|ghi\s*chu)\b', c_str):
            return True
      return False

    summary_mask = df.apply(is_footer_or_summary, axis=1)
    df = df[~summary_mask].copy()

    # Infer year from sheet name or file name if present
    inferred_year = None
    year_match = re.search(r'(?:20\d{2})', f'{sheet_name}_{file_name}')
    if year_match:
      inferred_year = int(year_match.group(0))

    # Clean dates and numbers
    for col in clean_cols:
      is_date_col = any(w in col for w in ['ngay', 'date', 'thoi_gian', 'han_dung', 'han_su_dung'])
      is_num_col = any(w in col for w in ['gia', 'tien', 'so_luong', 'sl', 'don_gia', 'thanh_tien', 'ton', 'ti_le', 'he_so'])

      if is_date_col:
        df[col] = df[col].apply(lambda x: parse_vietnamese_date(x, default_year=inferred_year))
      elif is_num_col:
        # Check if values contain strings with commas
        sample_str = any(isinstance(v, str) and (',' in v or '.' in v or 'đ' in v) for v in df[col].dropna().iloc[:10]) if not df[col].dropna().empty else False
        if sample_str or df[col].dtype == object:
          df[col] = df[col].apply(parse_clean_number)

    # Forward-fill order metadata
    df = self._forward_fill_order_group(df, clean_cols)

    # Deduplicate identical rows within the same order (Rule 8)
    key_col = next((c for c in clean_cols if c in self.ORDER_GROUP_KEYS), None)
    if key_col and key_col in df.columns:
      df = df.drop_duplicates()

    return df, col_map

  def load_excel_file(self, file_path: Path) -> List[Tuple[str, pd.DataFrame, Dict[str, str]]]:
    """Load an Excel file, grouping identical multi-sheet structures."""
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheets_data = []

    for sheet in wb.sheetnames:
      ws = wb[sheet]
      rows = list(ws.iter_rows(values_only=True))
      if not rows:
        continue

      hdr_idx = self._detect_header_row(rows)
      raw_header = rows[hdr_idx]
      header = [str(c).strip() if c is not None and str(c).strip() else f'col_{i}' for i, c in enumerate(raw_header)]
      data_rows = rows[hdr_idx + 1:]

      if not data_rows:
        continue

      df = pd.DataFrame(data_rows, columns=header)
      # Drop completely empty rows
      df = df.dropna(how='all')
      if df.empty:
        continue

      df_clean, col_map = self._clean_dataframe(df, sheet_name=sheet, file_name=file_path.stem)
      sheets_data.append((sheet, df_clean, col_map))

    wb.close()
    return sheets_data

  def load_csv_file(self, file_path: Path) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Load CSV with automatic delimiter and encoding detection."""
    encodings = ['utf-8', 'utf-8-sig', 'cp1258', 'latin-1']
    df = None
    for enc in encodings:
      try:
        df = pd.read_csv(file_path, encoding=enc, sep=None, engine='python')
        break
      except Exception:
        continue

    if df is None:
      raise ValueError(f'Could not read CSV file: {file_path}')

    df = df.dropna(how='all')
    df_clean, col_map = self._clean_dataframe(df, file_name=file_path.stem)
    return df_clean, col_map

  def load_sqlite_file(self, file_path: Path) -> List[Tuple[str, pd.DataFrame, Dict[str, str]]]:
    """Load tables from SQLite database."""
    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]

    results = []
    for t in tables:
      df = pd.read_sql_query(f'SELECT * FROM "{t}"', conn)
      df_clean, col_map = self._clean_dataframe(df, sheet_name=t, file_name=file_path.stem)
      results.append((t, df_clean, col_map))

    conn.close()
    return results

  def ingest_business(self, biz_dir: Path, calendar_path: Optional[Path] = None) -> List[str]:
    """Ingest all data files of a business into DuckDB. Returns list of loaded table names."""
    if calendar_path:
      self.load_calendar(calendar_path)

    loaded_tables = []
    # Temporary buffer for multi-sheet union: {table_base_name: [(df, col_map)]}
    table_groups: Dict[str, List[Tuple[pd.DataFrame, Dict[str, str]]]] = {}

    for file in sorted(biz_dir.iterdir()):
      if file.name == 'README.md':
        continue

      base_name = to_snake_case(file.stem)

      if file.suffix.lower() == '.csv':
        df, col_map = self.load_csv_file(file)
        table_name = base_name
        self.con.register('temp_df', df)
        self.con.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM temp_df')
        self.con.unregister('temp_df')
        self.column_mappings[table_name] = col_map
        self.table_sources[table_name] = file.name
        loaded_tables.append(table_name)

      elif file.suffix.lower() == '.xlsx':
        sheets_data = self.load_excel_file(file)
        if not sheets_data:
          continue

        # Check if sheets share identical columns (e.g. monthly sheets)
        first_cols = tuple(sheets_data[0][1].columns)
        all_same_schema = len(sheets_data) > 1 and all(tuple(s[1].columns) == first_cols for s in sheets_data)

        if all_same_schema or len(sheets_data) == 1:
          # Concatenate all sheets into one logical table named after the file
          combined_df = pd.concat([s[1] for s in sheets_data], ignore_index=True)
          col_map = sheets_data[0][2]
          table_name = base_name
          self.con.register('temp_df', combined_df)
          self.con.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM temp_df')
          self.con.unregister('temp_df')
          self.column_mappings[table_name] = col_map
          self.table_sources[table_name] = file.name
          loaded_tables.append(table_name)
        else:
          # Different schemas across sheets -> separate tables
          for sheet_name, df, col_map in sheets_data:
            clean_sheet = to_snake_case(sheet_name)
            table_name = f'{base_name}_{clean_sheet}'
            self.con.register('temp_df', df)
            self.con.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM temp_df')
            self.con.unregister('temp_df')
            self.column_mappings[table_name] = col_map
            self.table_sources[table_name] = f'{file.name}:{sheet_name}'
            loaded_tables.append(table_name)

      elif file.suffix.lower() == '.sqlite':
        sqlite_tables = self.load_sqlite_file(file)
        for tbl_name, df, col_map in sqlite_tables:
          table_name = f'{base_name}_{to_snake_case(tbl_name)}' if base_name != 'pos' else to_snake_case(tbl_name)
          self.con.register('temp_df', df)
          self.con.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM temp_df')
          self.con.unregister('temp_df')
          self.column_mappings[table_name] = col_map
          self.table_sources[table_name] = f'{file.name}:{tbl_name}'
          loaded_tables.append(table_name)

    return loaded_tables

  def close(self):
    self.con.close()

