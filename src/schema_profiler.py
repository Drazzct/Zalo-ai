"""Schema Profiler Module for Zalo AI DataMate.

Analyzes DuckDB tables and business README.md to generate rich, concise schema
metadata,
unit conversion factors, date bounds, and LLM-friendly context prompts.
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
from src.data_ingestor import DataIngestor


class SchemaProfiler:
  """Inspects ingested DuckDB tables and parses README.md to profile a business."""

  def __init__(self, ingestor: DataIngestor, biz_dir: Path):
    self.ingestor = ingestor
    self.con = ingestor.con
    self.biz_dir = biz_dir
    self.biz_id = biz_dir.name
    self.readme_text = self._read_readme()
    self.conventions = self._extract_conventions()
    self.unit_conversions = self._extract_unit_conversions()
    self.table_profiles = self._profile_tables()

  def _read_readme(self) -> str:
    readme_path = self.biz_dir / 'README.md'
    if readme_path.exists():
      try:
        return readme_path.read_text(encoding='utf-8')
      except Exception:
        pass
    return ''

  def _extract_conventions(self) -> List[str]:
    """Extract business conventions from README.md under '## Quy ước'."""
    conventions = []
    if not self.readme_text:
      return conventions

    capture = False
    for line in self.readme_text.splitlines():
      stripped = line.strip()
      if stripped.startswith('##') and 'quy ước' in stripped.lower():
        capture = True
        continue
      if capture:
        if stripped.startswith('##') and not stripped.startswith('###'):
          break
        if stripped.startswith('-') or stripped.startswith('*'):
          conventions.append(stripped.lstrip('-*').strip())

    return conventions

  def _extract_unit_conversions(self) -> List[str]:
    """Extract unit conversion lines from README.md."""
    conversions = []
    if not self.readme_text:
      return conversions

    capture = False
    for line in self.readme_text.splitlines():
      stripped = line.strip()
      if 'quy đổi đơn vị' in stripped.lower():
        capture = True
        continue
      if capture:
        if stripped.startswith('##') or stripped.startswith('#'):
          break
        if stripped.startswith('-') or stripped.startswith('*'):
          conversions.append(stripped.lstrip('-*').strip())

    return conversions

  def _profile_tables(self) -> Dict[str, Dict[str, Any]]:
    """Profile every table in the DuckDB database."""
    profiles = {}
    tbl_res = self.con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema ="
        " 'main' AND table_name != 'calendar'"
    ).fetchall()
    table_names = [r[0] for r in tbl_res]

    for tbl in table_names:
      count_res = self.con.execute(
          f'SELECT COUNT(*) FROM "{tbl}"'
      ).fetchone()
      row_count = count_res[0] if count_res else 0

      col_res = self.con.execute(
          'SELECT column_name, data_type FROM information_schema.columns WHERE'
          f" table_name = '{tbl}'"
      ).fetchall()

      cols_info = {}
      min_date, max_date = None, None

      for col_name, dtype in col_res:
        # Get sample non-null values
        sample_res = self.con.execute(
            f'SELECT DISTINCT "{col_name}" FROM "{tbl}" WHERE "{col_name}" IS'
            ' NOT NULL LIMIT 3'
        ).fetchall()
        samples = [r[0] for r in sample_res if r[0] is not None]

        # Check if date column to get min/max
        is_date_col = any(
            w in col_name.lower()
            for w in ['ngay', 'date', 'thoi_gian', 'han_dung']
        )
        if is_date_col and row_count > 0:
          date_bounds = self.con.execute(
              f'SELECT MIN("{col_name}"), MAX("{col_name}") FROM "{tbl}" WHERE'
              f' "{col_name}" IS NOT NULL'
          ).fetchone()
          if date_bounds and date_bounds[0] and date_bounds[1]:
            min_date, max_date = str(date_bounds[0]), str(date_bounds[1])

        orig_name = self.ingestor.column_mappings.get(tbl, {}).get(
            col_name, col_name
        )
        cols_info[col_name] = {
            'orig_name': orig_name,
            'type': dtype,
            'samples': samples[:3],
        }

      profiles[tbl] = {
          'rows': row_count,
          'min_date': min_date,
          'max_date': max_date,
          'columns': cols_info,
          'source': self.ingestor.table_sources.get(tbl, ''),
      }

    return profiles

  def get_overall_date_bounds(self) -> Tuple[Optional[str], Optional[str]]:
    """Return earliest and latest dates across all business tables."""
    min_dates = [
        p['min_date'] for p in self.table_profiles.values() if p['min_date']
    ]
    max_dates = [
        p['max_date'] for p in self.table_profiles.values() if p['max_date']
    ]
    min_d = min(min_dates) if min_dates else None
    max_d = max(max_dates) if max_dates else None
    return min_d, max_d

  def to_prompt_context(self, focus_table: Optional[str] = None) -> str:
    """Format schema and README into a concise LLM prompt string.

    If focus_table is specified and there are many tables (> 3), displays full
    column details and samples for the focus table and lookup/dimension tables,
    while non-relevant partition tables are rendered in a compact 1-line format.
    """
    lines = [f'### CƠ SỞ DỮ LIỆU CỬA HÀNG: {self.biz_id}']

    # Determine detailed vs compact tables
    detailed_tables = set()
    compact_tables = set()

    if focus_table and len(self.table_profiles) > 3:
      detailed_tables.add(focus_table)
      for tbl, p in self.table_profiles.items():
        if tbl == focus_table:
          continue
        # Dimension or lookup tables (no date range or small row count or master tables)
        is_lookup = (
            p['min_date'] is None
            or p['rows'] < 2000
            or any(w in tbl.lower() for w in ['danh_sach', 'thuoc', 'khach', 'san_pham', 'loai', 'ncc', 'ncc_'])
        )
        if is_lookup:
          detailed_tables.add(tbl)
        else:
          compact_tables.add(tbl)
    else:
      detailed_tables = set(self.table_profiles.keys())

    # 1. Output detailed tables
    for tbl in self.table_profiles:
      if tbl not in detailed_tables:
        continue
      p = self.table_profiles[tbl]
      date_str = (
          f' (Kỳ: {p["min_date"]} đến {p["max_date"]})'
          if p['min_date'] and p['max_date']
          else ''
      )
      prefix = 'Bảng chính: ' if focus_table and tbl == focus_table else 'Bảng: '
      lines.append(f'\n{prefix}`{tbl}` ({p["rows"]} dòng{date_str})')
      lines.append('Cột:')
      for col, cinfo in p['columns'].items():
        sample_str = ', '.join([repr(s) for s in cinfo['samples']])
        sample_disp = f' [Ví dụ: {sample_str}]' if sample_str else ''
        lines.append(f"  - `{col}` ({cinfo['type']}){sample_disp}")

    # 2. Output compact tables if any
    if compact_tables:
      lines.append('\nCác bảng dữ liệu kỳ khác (rút gọn):')
      for tbl in self.table_profiles:
        if tbl not in compact_tables:
          continue
        p = self.table_profiles[tbl]
        date_str = (
            f' (Kỳ: {p["min_date"]} đến {p["max_date"]})'
            if p['min_date'] and p['max_date']
            else ''
        )
        col_list = ', '.join([f'`{c}`' for c in p['columns'].keys()])
        lines.append(f'- Bảng `{tbl}` ({p["rows"]} dòng{date_str}): {col_list}')

    if self.unit_conversions:
      lines.append('\n### QUY ĐỔI ĐƠN VỊ (README):')
      for conv in self.unit_conversions[:15]:
        lines.append(f'- {conv}')

    if self.conventions:
      # Filter out duplicate lines already present in unit_conversions
      unique_convs = [c for c in self.conventions if c not in self.unit_conversions]
      if unique_convs:
        lines.append('\n### QUY ƯỚC NGHIỆP VỤ CỬA HÀNG (README):')
        for conv in unique_convs[:15]:
          lines.append(f'- {conv}')

    return '\n'.join(lines)

