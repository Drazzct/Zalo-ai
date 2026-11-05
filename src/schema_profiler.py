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

  def to_prompt_context(self) -> str:
    """Format schema and README into a concise LLM prompt string."""
    lines = [f'### CƠ SỞ DỮ LIỆU CỬA HÀNG: {self.biz_id}']

    for tbl, p in self.table_profiles.items():
      date_str = (
          f' (Kỳ: {p["min_date"]} đến {p["max_date"]})'
          if p['min_date'] and p['max_date']
          else ''
      )
      lines.append(f'\nBảng: `{tbl}` ({p["rows"]} dòng{date_str})')
      lines.append('Cột:')
      for col, cinfo in p['columns'].items():
        sample_str = ', '.join([repr(s) for s in cinfo['samples']])
        sample_disp = f' [Ví dụ: {sample_str}]' if sample_str else ''
        lines.append(f"  - `{col}` ({cinfo['type']}){sample_disp}")

    if self.unit_conversions:
      lines.append('\n### QUY ĐỔI ĐƠN VỊ (README):')
      for conv in self.unit_conversions[:15]:
        lines.append(f'- {conv}')

    return '\n'.join(lines)

