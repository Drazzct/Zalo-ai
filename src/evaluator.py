"""Evaluation Engine for Zalo AI DataMate.

Calculates the official competition metric:
Score = Correct (+1) - Wrong (-1) + Abstain (0).
Strictly follows Rule 9 for answer verification across all 9 types.
"""

from collections import Counter
import json
import math
import unicodedata
from typing import Any, Dict, List, Optional, Tuple


def normalize_str(s: Any) -> str:
  """Normalize Vietnamese string: NFC, strip, lowercase, collapse whitespace."""
  if s is None:
    return ''
  text = str(s).strip()
  text = unicodedata.normalize('NFC', text)
  text = ' '.join(text.split())
  return text.lower()


class Evaluator:
  """Evaluates model predictions against ground truth according to Zalo AI competition rules."""

  @staticmethod
  def match_number(pred: Any, gt: Any) -> bool:
    try:
      p_val = float(pred)
      g_val = float(gt)
      # Check if both are integers or money values
      if g_val.is_integer():
        return int(round(p_val)) == int(round(g_val))
      return math.isclose(p_val, g_val, rel_tol=1e-3, abs_tol=1e-3)
    except (ValueError, TypeError):
      return False

  @staticmethod
  def match_percent(pred: Any, gt: Any) -> bool:
    try:
      p_val = round(float(pred), 2)
      g_val = round(float(gt), 2)
      return p_val == g_val
    except (ValueError, TypeError):
      return False

  @staticmethod
  def match_date(pred: Any, gt: Any) -> bool:
    p_str = normalize_str(pred)
    g_str = normalize_str(gt)
    return p_str == g_str

  @staticmethod
  def match_boolean(pred: Any, gt: Any) -> bool:
    if isinstance(pred, str):
      if pred.lower() in ('true', 'đúng', '1'):
        pred = True
      elif pred.lower() in ('false', 'sai', '0'):
        pred = False
    return bool(pred) is bool(gt)

  @staticmethod
  def match_string(pred: Any, gt: Any, aliases: Optional[List[str]] = None) -> bool:
    p_str = normalize_str(pred)
    g_str = normalize_str(gt)
    if p_str == g_str:
      return True

    # Check aliases
    if aliases:
      for alias in aliases:
        if p_str == normalize_str(alias):
          return True

    return False

  @staticmethod
  def match_list(pred: Any, gt: Any) -> bool:
    if not isinstance(pred, list) or not isinstance(gt, list):
      return False
    if len(pred) != len(gt):
      return False

    for p_elem, g_elem in zip(pred, gt):
      if isinstance(g_elem, (int, float)):
        if not Evaluator.match_number(p_elem, g_elem):
          return False
      else:
        if normalize_str(p_elem) != normalize_str(g_elem):
          return False
    return True

  @staticmethod
  def match_table(pred: Any, gt: Any) -> bool:
    """Rule 137: Column names or positions, rows match regardless of row order."""
    if not isinstance(pred, dict) or not isinstance(gt, dict):
      return False

    p_cols = pred.get('columns', [])
    g_cols = gt.get('columns', [])
    if len(p_cols) != len(g_cols):
      return False

    p_rows = pred.get('rows', [])
    g_rows = gt.get('rows', [])
    if len(p_rows) != len(g_rows):
      return False

    # Normalize rows for comparison
    def norm_row(row):
      normed = []
      for cell in row:
        if isinstance(cell, (int, float)):
          normed.append(round(float(cell), 2))
        else:
          normed.append(normalize_str(cell))
      return tuple(normed)

    p_set = Counter([norm_row(r) for r in p_rows])
    g_set = Counter([norm_row(r) for r in g_rows])
    return p_set == g_set

  @classmethod
  def check_answer(
      cls,
      pred_obj: Dict[str, Any],
      gt_obj: Dict[str, Any]
  ) -> Tuple[bool, str]:
    """Check a single prediction object against ground truth object.

    Returns (is_correct, status_str):
    status_str in ('correct', 'wrong', 'abstain').
    """
    pred_type = pred_obj.get('type')
    gt_type = gt_obj.get('type')

    # If prediction is abstain
    if pred_type == 'abstain' or pred_type is None:
      return False, 'abstain'

    # Unanswerable match
    if gt_type == 'unanswerable':
      if pred_type == 'unanswerable':
        return True, 'correct'
      else:
        return False, 'wrong'

    # If predicted unanswerable when ground truth had answer
    if pred_type == 'unanswerable':
      return False, 'wrong'

    # Type must match
    if pred_type != gt_type:
      return False, 'wrong'

    pred_ans = pred_obj.get('answer')
    gt_ans = gt_obj.get('answer')
    aliases = gt_obj.get('alias', [])

    matched = False
    if gt_type == 'number':
      matched = cls.match_number(pred_ans, gt_ans)
    elif gt_type == 'percent':
      matched = cls.match_percent(pred_ans, gt_ans)
    elif gt_type == 'date':
      matched = cls.match_date(pred_ans, gt_ans)
    elif gt_type == 'boolean':
      matched = cls.match_boolean(pred_ans, gt_ans)
    elif gt_type == 'string':
      matched = cls.match_string(pred_ans, gt_ans, aliases)
    elif gt_type == 'list':
      matched = cls.match_list(pred_ans, gt_ans)
    elif gt_type == 'table':
      matched = cls.match_table(pred_ans, gt_ans)

    return (True, 'correct') if matched else (False, 'wrong')

  @classmethod
  def evaluate(
      cls,
      predictions: List[Dict[str, Any]],
      ground_truth: List[Dict[str, Any]]
  ) -> Dict[str, Any]:
    """Evaluate full list of predictions against ground truth.

    Missing predictions are treated as abstain (0 points).
    """
    pred_map = {p['id']: p for p in predictions if 'id' in p}
    gt_map = {g['id']: g for g in ground_truth if 'id' in g}

    correct_cnt = 0
    wrong_cnt = 0
    abstain_cnt = 0

    type_stats = {}
    details = []

    for qid, gt_obj in gt_map.items():
      gt_type = gt_obj.get('type', 'unknown')
      if gt_type not in type_stats:
        type_stats[gt_type] = {'total': 0, 'correct': 0, 'wrong': 0, 'abstain': 0}
      type_stats[gt_type]['total'] += 1

      if qid not in pred_map:
        abstain_cnt += 1
        type_stats[gt_type]['abstain'] += 1
        details.append({'id': qid, 'type': gt_type, 'result': 'abstain (missing)'})
      else:
        pred_obj = pred_map[qid]
        is_corr, status = cls.check_answer(pred_obj, gt_obj)
        if status == 'correct':
          correct_cnt += 1
          type_stats[gt_type]['correct'] += 1
        elif status == 'wrong':
          wrong_cnt += 1
          type_stats[gt_type]['wrong'] += 1
        else:
          abstain_cnt += 1
          type_stats[gt_type]['abstain'] += 1

        details.append({
            'id': qid,
            'type': gt_type,
            'result': status,
            'gt': gt_obj.get('answer'),
            'pred': pred_obj.get('answer')
        })

    total_score = correct_cnt * 1 - wrong_cnt * 1
    total_q = len(gt_map)

    return {
        'total_questions': total_q,
        'correct': correct_cnt,
        'wrong': wrong_cnt,
        'abstain': abstain_cnt,
        'total_score': total_score,
        'accuracy': (correct_cnt / total_q) * 100 if total_q > 0 else 0,
        'type_stats': type_stats,
        'details': details
    }
