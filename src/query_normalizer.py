"""Query Normalizer and Temporal Anchor Module for Zalo AI DataMate.

Normalizes Vietnamese abbreviations and teencode, and resolves relative
temporal expressions (e.g. 'tháng này', 'hôm nay', 'tuần trước', 'Tết năm Y')
into exact date ranges using CalendarResolver.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
from src.calendar_resolver import CalendarResolver


class QueryNormalizer:
  """Normalizes Vietnamese teencode and extracts exact date bounds for relative time expressions."""

  TEENCODE_MAP = [
      (r'\bdthu\b', 'doanh thu'),
      (r'\bdt\b', 'doanh thu'),
      (r'\bbnhiu\b', 'bao nhiêu'),
      (r'\bbao nhiu\b', 'bao nhiêu'),
      (r'\bbn\b', 'bao nhiêu'),
      (r'\bhnay\b', 'hôm nay'),
      (r'\bhqua\b', 'hôm qua'),
      (r'\bthg\b', 'tháng'),
      (r'\btuan nay\b', 'tuần này'),
      (r'\btuan trc\b', 'tuần trước'),
      (r'\btuan roi\b', 'tuần rồi'),
      (r'\btuan qua\b', 'tuần trước'),
      (r'\bnam trc\b', 'năm trước'),
      (r'\bnam nay\b', 'năm nay'),
      (r'\bdau nam\b', 'đầu năm'),
      (r'\bko\b', 'không'),
      (r'\bk\b', 'không'),
      (r'\bhok\b', 'không'),
      (r'\bhong\b', 'không'),
      (r'\bnhìu\b', 'nhiều'),
      (r'\bnhieu\b', 'nhiều'),
      (r'\bchay nhat\b', 'bán chạy nhất'),
      (r'\bchạy nhất\b', 'bán chạy nhất'),
      (r'\bvaayj\b', 'vậy'),
      (r'\bz\b', 'vậy'),
      (r'\bđc\b', 'được'),
      (r'\bdc\b', 'được'),
      (r'\bgium\b', 'giúp'),
      (r'\bgiùm\b', 'giúp'),
      (r'\bvs\b', 'với'),
      (r'\btrc\b', 'trước'),
  ]

  def __init__(self, calendar_resolver: Optional[CalendarResolver] = None):
    self.calendar = calendar_resolver

  def normalize_text(self, text: str) -> str:
    """Normalize abbreviations, teencode, and multiple spaces."""
    res = text
    for pattern, repl in self.TEENCODE_MAP:
      res = re.sub(pattern, repl, res, flags=re.IGNORECASE)
    res = ' '.join(res.split())
    return res

  def extract_temporal_bounds(
      self,
      question: str,
      as_of_date_str: str
  ) -> Dict[str, Any]:
    """Identify time expressions in the question and compute exact date ranges based on as_of_date."""
    as_of = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
    norm_q = self.normalize_text(question).lower()

    anchors = {
        'as_of_date': as_of_date_str,
        'detected_phrases': [],
        'primary_window': None,  # (start_date_str, end_date_str)
        'compare_window': None,  # For growth / comparison queries
    }

    # 1. Hôm nay
    if any(w in norm_q for w in ['hôm nay', 'hom nay', 'hnay', 'trong ngày', 'trong ngay']):
      anchors['detected_phrases'].append('hôm nay')
      anchors['primary_window'] = (as_of_date_str, as_of_date_str)

    # 2. Hôm qua
    elif any(w in norm_q for w in ['hôm qua', 'hom qua', 'hqua']):
      anchors['detected_phrases'].append('hôm qua')
      yest = (as_of - timedelta(days=1)).strftime('%Y-%m-%d')
      anchors['primary_window'] = (yest, yest)

    # 3. N ngày gần nhất (e.g. 7 ngày gần nhất, 7 ngày qua, 30 ngày gần đây)
    n_days_match = re.search(r'(\d+)\s+(?:ngày|ngay)\s+(?:gần\s+nhất|gan\s+nhat|qua|gần\s+đây|gan\s+day)', norm_q)
    if n_days_match and self.calendar:
      n = int(n_days_match.group(1))
      anchors['detected_phrases'].append(f'{n} ngày gần nhất')
      s_d, e_d = self.calendar.get_n_recent_days(as_of, n)
      anchors['primary_window'] = (s_d.strftime('%Y-%m-%d'), e_d.strftime('%Y-%m-%d'))

    # 4. Tuần này
    elif any(w in norm_q for w in ['tuần này', 'tuan nay']) and self.calendar:
      anchors['detected_phrases'].append('tuần này')
      s_d, e_d = self.calendar.get_week_window(as_of, 'this_week')
      anchors['primary_window'] = (s_d.strftime('%Y-%m-%d'), e_d.strftime('%Y-%m-%d'))

    # 5. Tuần trước / tuần rồi
    elif any(w in norm_q for w in ['tuần trước', 'tuan truoc', 'tuần rồi', 'tuan roi', 'tuần qua', 'tuan qua']) and self.calendar:
      anchors['detected_phrases'].append('tuần trước')
      s_d, e_d = self.calendar.get_week_window(as_of, 'prev_week')
      anchors['primary_window'] = (s_d.strftime('%Y-%m-%d'), e_d.strftime('%Y-%m-%d'))

    # 6. Tháng này
    elif any(w in norm_q for w in ['tháng này', 'thang nay']) and self.calendar:
      anchors['detected_phrases'].append('tháng này')
      s_d, e_d = self.calendar.get_month_window(as_of, 'this_month')
      anchors['primary_window'] = (s_d.strftime('%Y-%m-%d'), e_d.strftime('%Y-%m-%d'))

      # Check if comparison with last month
      if any(w in norm_q for w in ['so với tháng trước', 'so vs thang truoc', 'tăng trưởng', 'tang truong', 'thay đổi', 'thay doi']):
        prev_s, prev_e = self.calendar.get_month_window(as_of, 'same_period_last_month')
        anchors['compare_window'] = (prev_s.strftime('%Y-%m-%d'), prev_e.strftime('%Y-%m-%d'))

    # 7. Cụ thể: tháng M/Y, tháng M năm Y, thM/Y, tM/Y, 02/2026, 9/2025
    month_match = re.search(r'(?:(?:tháng|thang|th|t)\s*(\d{1,2})|(?:\b|\s)(\d{1,2}))(?:/|-|\s+(?:năm|nam)\s*)(\d{4})', norm_q)
    if month_match and self.calendar:
      m = int(month_match.group(1) or month_match.group(2))
      y = int(month_match.group(3))
      if 1 <= m <= 12 and 2020 <= y <= 2035:
        anchors['detected_phrases'].append(f'tháng {m}/{y}')
        m_date = date(y, m, 1)
        s_d, e_d = self.calendar.get_month_window(m_date, 'full_month')
        anchors['primary_window'] = (s_d.strftime('%Y-%m-%d'), e_d.strftime('%Y-%m-%d'))

        # Check comparison with previous month
        if any(w in norm_q for w in ['so với tháng', 'so vs thang', 'tăng trưởng', 'tang truong', 'thay đổi', 'thay doi']):
          prev_m = 12 if m == 1 else m - 1
          prev_y = y - 1 if m == 1 else y
          prev_s_d, prev_e_d = self.calendar.get_month_window(date(prev_y, prev_m, 1), 'full_month')
          anchors['compare_window'] = (prev_s_d.strftime('%Y-%m-%d'), prev_e_d.strftime('%Y-%m-%d'))

    # 8. Quý Q/Y hoặc quý Q năm Y (e.g. quý 2/2026, quy 3 nam 2025, q3/2026)
    quarter_match = re.search(r'(?:quý|quy|q)\s*([1-4])(?:/|-|\s+(?:năm|nam)\s*|\s+)(\d{4})', norm_q)
    if quarter_match and self.calendar:
      q, y = int(quarter_match.group(1)), int(quarter_match.group(2))
      anchors['detected_phrases'].append(f'quý {q}/{y}')
      s_d, e_d = self.calendar.get_quarter_window(y, q)
      anchors['primary_window'] = (s_d.strftime('%Y-%m-%d'), e_d.strftime('%Y-%m-%d'))

    # 9. Tết năm Y (e.g. Tết 2026, Dịp Tết Nguyên đán 2026, Tết năm 2025)
    tet_match = re.search(r'(?:dịp\s+)?(?:tết|tet)(?:\s+nguyên\s+đán|\s+nguyen\s+dan)?\s+(?:năm\s+|nam\s+)?(\d{4})', norm_q)
    if tet_match and self.calendar:
      y = int(tet_match.group(1))
      anchors['detected_phrases'].append(f'Tết năm {y}')
      try:
        s_d, e_d = self.calendar.get_tet_window(y)
        anchors['primary_window'] = (s_d.strftime('%Y-%m-%d'), e_d.strftime('%Y-%m-%d'))
        pre_s, pre_e = self.calendar.get_pre_tet_window(y)
        anchors['compare_window'] = (pre_s.strftime('%Y-%m-%d'), pre_e.strftime('%Y-%m-%d'))
      except Exception:
        pass

    # 10. Từ đầu năm
    elif any(w in norm_q for w in ['từ đầu năm', 'tu dau nam', 'đầu năm tới nay', 'dau nam toi nay']) and self.calendar:
      anchors['detected_phrases'].append('từ đầu năm')
      s_d, e_d = self.calendar.get_year_to_date(as_of)
      anchors['primary_window'] = (s_d.strftime('%Y-%m-%d'), e_d.strftime('%Y-%m-%d'))

    return anchors

