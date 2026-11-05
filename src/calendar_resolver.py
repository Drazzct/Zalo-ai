"""Calendar Resolver Module for Zalo AI DataMate.

Handles solar and lunar dates, public holidays, Vietnamese Tet windows, and
relative temporal calculations according to rulebook rules.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd


class CalendarResolver:
  """Resolves solar/lunar dates and relative time windows based on calendar.csv."""

  def __init__(self, calendar_path: Path):
    if not calendar_path.exists():
      raise FileNotFoundError(f'Calendar file not found: {calendar_path}')

    self.df = pd.read_csv(calendar_path)
    self.df['date'] = pd.to_datetime(self.df['date']).dt.date
    self.date_to_row = {
        row['date']: row.to_dict() for _, row in self.df.iterrows()
    }

  def get_row(self, d: date) -> Optional[dict]:
    return self.date_to_row.get(d)

  def get_tet_window(self, lunar_year: int) -> Tuple[date, date]:
    """Tết năm Y: từ 23 tháng Chạp (năm âm Y - 1) đến hết mùng 10 tháng Giêng (năm âm Y).

    Rule 35: từ ngày dương của 23 tháng Chạp (năm âm Y - 1) đến hết ngày dương
    của
    mùng 10 tháng Giêng (năm âm Y).
    """
    # Find 23 Chạp (tháng 12) of lunar_year - 1
    start_candidates = self.df[
        (self.df['lunar_year'] == lunar_year - 1)
        & (self.df['lunar_month'] == 12)
        & (self.df['lunar_day'] == 23)
        & (~self.df['lunar_leap'])
    ]
    if start_candidates.empty:
      raise ValueError(f'Cannot find 23 Chạp for lunar year {lunar_year - 1}')
    start_date = start_candidates.iloc[0]['date']

    # Find mùng 10 tháng 1 of lunar_year
    end_candidates = self.df[
        (self.df['lunar_year'] == lunar_year)
        & (self.df['lunar_month'] == 1)
        & (self.df['lunar_day'] == 10)
        & (~self.df['lunar_leap'])
    ]
    if end_candidates.empty:
      raise ValueError(
          f'Cannot find mùng 10 tháng 1 for lunar year {lunar_year}'
      )
    end_date = end_candidates.iloc[0]['date']

    return start_date, end_date

  def get_pre_tet_window(self, lunar_year: int) -> Tuple[date, date]:
    """So với trước Tết = cùng số ngày ngay trước 23 tháng Chạp (Rule 35)."""
    start_tet, end_tet = self.get_tet_window(lunar_year)
    tet_days = (end_tet - start_tet).days + 1
    pre_end = start_tet - timedelta(days=1)
    pre_start = pre_end - timedelta(days=tet_days - 1)
    return pre_start, pre_end

  def get_week_window(
      self, as_of_date: date, week_type: str = 'this_week'
  ) -> Tuple[date, date]:
    """Week starts Monday (Rule 30).

    this_week: Monday of as_of_date's week to as_of_date (inclusive).
    prev_week: Monday to Sunday of previous week.
    """
    # weekday(): Monday is 0, Sunday is 6
    day_of_week = as_of_date.weekday()
    monday_this_week = as_of_date - timedelta(days=day_of_week)

    if week_type == 'this_week':
      return monday_this_week, as_of_date
    elif week_type in ('prev_week', 'last_week'):
      monday_prev_week = monday_this_week - timedelta(days=7)
      sunday_prev_week = monday_prev_week + timedelta(days=6)
      return monday_prev_week, sunday_prev_week
    else:
      raise ValueError(f'Unknown week_type: {week_type}')

  def get_month_window(
      self, as_of_date: date, month_type: str = 'this_month'
  ) -> Tuple[date, date]:
    """Month window calculation according to Rule 31 & 32.

    this_month: 1st of month to as_of_date.
    same_period_last_month: 1st of last month to min(last_day_of_last_month,
    same_day_as_of_date).
    full_month: 1st of month to last day of month.
    """
    year = as_of_date.year
    month = as_of_date.month

    if month_type == 'this_month':
      start_date = date(year, month, 1)
      return start_date, as_of_date

    elif month_type == 'same_period_last_month':
      if month == 1:
        prev_year = year - 1
        prev_month = 12
      else:
        prev_year = year
        prev_month = month - 1

      start_date = date(prev_year, prev_month, 1)
      # Find max days in prev_month
      if prev_month == 12:
        next_month_start = date(prev_year + 1, 1, 1)
      else:
        next_month_start = date(prev_year, prev_month + 1, 1)
      max_day_prev = (next_month_start - timedelta(days=1)).day
      end_day = min(as_of_date.day, max_day_prev)
      end_date = date(prev_year, prev_month, end_day)
      return start_date, end_date

    elif month_type == 'full_month':
      start_date = date(year, month, 1)
      if month == 12:
        next_month_start = date(year + 1, 1, 1)
      else:
        next_month_start = date(year, month + 1, 1)
      end_date = next_month_start - timedelta(days=1)
      return start_date, end_date

    else:
      raise ValueError(f'Unknown month_type: {month_type}')

  def get_n_recent_days(self, as_of_date: date, n: int) -> Tuple[date, date]:
    """Rule 28: N ngày gần nhất = N ngày liền nhau kể cả hôm nay, ngày cuối là hôm nay."""
    start_date = as_of_date - timedelta(days=n - 1)
    return start_date, as_of_date

  def get_year_to_date(self, as_of_date: date) -> Tuple[date, date]:
    """Rule 33: Từ đầu năm, từ đầu năm tới nay = 01/01 năm nay đến hết hôm nay."""
    return date(as_of_date.year, 1, 1), as_of_date

  def get_quarter_window(self, year: int, quarter: int) -> Tuple[date, date]:
    """Rule 34: Quý Q theo dương lịch, mỗi quý 3 tháng tính từ tháng 1."""
    start_month = (quarter - 1) * 3 + 1
    start_date = date(year, start_month, 1)
    end_month = start_month + 2
    if end_month == 12:
      end_date = date(year, 12, 31)
    else:
      end_date = date(year, end_month + 1, 1) - timedelta(days=1)
    return start_date, end_date
