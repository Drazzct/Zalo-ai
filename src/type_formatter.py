"""Strict Type Formatter Module for Zalo AI DataMate.

Enforces Rule 9 formatting rules for all 9 output types:
number, percent, date, boolean, string, list, table, unanswerable, abstain.
Fixes common formatting slip-ups (e.g. currency symbols, percent signs, raw
strings).
"""

from datetime import date, datetime
import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from src.data_ingestor import parse_clean_number, parse_vietnamese_date


class TypeFormatter:
  """Formats and validates output objects to strictly comply with competition Rule 9."""

  VALID_TYPES = {
      'number',
      'percent',
      'date',
      'boolean',
      'string',
      'list',
      'table',
      'unanswerable',
      'abstain',
  }

  @classmethod
  def format_number(
      cls, val: Any, is_money_or_count: bool = False
  ) -> Optional[Union[int, float]]:
    """Format into JSON number (int or float). Money and counts must be integer VND."""
    num = parse_clean_number(val)
    if num is None or math.isnan(num) or math.isinf(num):
      return None

    if is_money_or_count or num.is_integer():
      return int(round(num))
    return round(num, 4)

  @classmethod
  def format_percent(cls, val: Any) -> Optional[float]:
    """Format into percentage number with 2 decimal places (e.g. 12.45, -5.20)."""
    if val is None:
      return None

    # Handle string with %
    if isinstance(val, str):
      val = val.replace('%', '').strip()

    num = parse_clean_number(val)
    if num is None or math.isnan(num) or math.isinf(num):
      return None

    return round(float(num), 2)

  @classmethod
  def format_date(cls, val: Any) -> Optional[str]:
    """Format into YYYY-MM-DD or YYYY-MM."""
    if val is None:
      return None

    # If datetime or date
    if isinstance(val, (datetime, date)):
      return val.strftime('%Y-%m-%d')

    s = str(val).strip()
    # Check if YYYY-MM format
    if re.match(r'^\d{4}-\d{2}$', s):
      return s

    # Parse with vietnamese date parser
    parsed = parse_vietnamese_date(s)
    if parsed:
      # If has time part, strip time to keep YYYY-MM-DD
      return parsed.split()[0]
    return s if re.match(r'^\d{4}-\d{2}-\d{2}$', s) else None

  @classmethod
  def format_boolean(cls, val: Any) -> Optional[bool]:
    """Format into pure boolean True or False."""
    if isinstance(val, bool):
      return val
    if isinstance(val, (int, float)):
      return bool(val)
    if isinstance(val, str):
      s = val.strip().lower()
      if s in ('true', 'có', 'đúng', 'yes', '1'):
        return True
      if s in ('false', 'không', 'sai', 'no', '0'):
        return False
    return None

  @classmethod
  def format_string(cls, val: Any) -> Optional[str]:
    """Format into string (preserve casing and accents, strip whitespace)."""
    if val is None:
      return None
    s = str(val).strip()
    # If returned as a 1-element list by mistake
    if isinstance(val, list) and len(val) == 1:
      s = str(val[0]).strip()
    return s if s else None

  @classmethod
  def format_list(cls, val: Any) -> Optional[List[Any]]:
    """Format into JSON list."""
    if val is None:
      return None

    # If returned as comma separated string: "Cà phê sữa, Bạc xỉu"
    if isinstance(val, str):
      items = [item.strip() for item in val.split(',') if item.strip()]
      val = items

    if not isinstance(val, list):
      val = [val]

    formatted_list = []
    for item in val:
      if isinstance(item, (int, float)):
        formatted_list.append(
            int(item) if float(item).is_integer() else round(item, 2)
        )
      elif isinstance(item, str):
        # Check if number string
        num_clean = parse_clean_number(item)
        if num_clean is not None and (
            item.isdigit() or item.replace(',', '').isdigit()
        ):
          formatted_list.append(int(round(num_clean)))
        else:
          formatted_list.append(item.strip())
      else:
        formatted_list.append(item)

    return formatted_list

  @classmethod
  def format_table(cls, val: Any) -> Optional[Dict[str, Any]]:
    """Format into {"columns": [...], "rows": [[...], ...]}."""
    if not isinstance(val, dict):
      return None

    cols = val.get('columns', [])
    rows = val.get('rows', [])
    if not isinstance(cols, list) or not isinstance(rows, list):
      return None

    formatted_cols = [str(c).strip() for c in cols]
    formatted_rows = []

    for r in rows:
      if not isinstance(r, (list, tuple)):
        continue
      formatted_cell_row = []
      for cell in r:
        num_val = parse_clean_number(cell)
        if num_val is not None and any(ch.isdigit() for ch in str(cell)):
          formatted_cell_row.append(int(round(num_val)) if num_val.is_integer() else round(num_val, 2))
        elif isinstance(cell, (int, float)):
          formatted_cell_row.append(int(cell) if float(cell).is_integer() else round(cell, 2))
        else:
          formatted_cell_row.append(str(cell).strip() if cell is not None else '')
      formatted_rows.append(formatted_cell_row)

    return {'columns': formatted_cols, 'rows': formatted_rows}

  @classmethod
  def format_answer_object(
      cls,
      raw_obj: Dict[str, Any],
      question_text: str = ''
  ) -> Dict[str, Any]:
    """Enforce strict Rule 9 schema on any raw output object.

    Returns valid submission object: {"id": ..., "type": ..., "answer": ...} or {"type": "abstain"}
    """
    qid = raw_obj.get('id', '')
    ans_type = raw_obj.get('type')

    if ans_type not in cls.VALID_TYPES or ans_type == 'abstain':
      return {'id': qid, 'type': 'abstain'} if qid else {'type': 'abstain'}

    if ans_type == 'unanswerable':
      reason = raw_obj.get('reason', 'Không đủ dữ liệu')
      res = {'type': 'unanswerable', 'reason': str(reason)}
      if qid:
        res['id'] = qid
      return res

    raw_ans = raw_obj.get('answer')
    if raw_ans is None:
      return {'id': qid, 'type': 'abstain'} if qid else {'type': 'abstain'}

    # Detect if money or item count question
    q_lower = question_text.lower()
    is_money_or_count = any(
        w in q_lower
        for w in ['tiền', 'doanh thu', 'dthu', 'giá', 'nợ', 'chi phí', 'lãi', 'số đơn', 'mấy', 'bao nhiêu đơn']
    )

    formatted_ans = None
    if ans_type == 'number':
      formatted_ans = cls.format_number(raw_ans, is_money_or_count=is_money_or_count)
    elif ans_type == 'percent':
      formatted_ans = cls.format_percent(raw_ans)
    elif ans_type == 'date':
      formatted_ans = cls.format_date(raw_ans)
    elif ans_type == 'boolean':
      formatted_ans = cls.format_boolean(raw_ans)
    elif ans_type == 'string':
      formatted_ans = cls.format_string(raw_ans)
    elif ans_type == 'list':
      formatted_ans = cls.format_list(raw_ans)
    elif ans_type == 'table':
      formatted_ans = cls.format_table(raw_ans)

    if formatted_ans is None:
      # If formatting failed, abstain to avoid -1 penalty!
      return {'id': qid, 'type': 'abstain'} if qid else {'type': 'abstain'}

    res = {'type': ans_type, 'answer': formatted_ans}
    if qid:
      res['id'] = qid
    return res
