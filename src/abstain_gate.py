"""Risk-Calibrated Abstention Policy and Quality Gate Module.

Implements the game-theoretic decision gate to optimize expected score:
E[Score] = P(correct) * (+1) - P(wrong) * (-1) + P(abstain) * 0.
Abstains whenever risk of error exceeds threshold, avoiding negative penalties.
"""

import math
from typing import Any, Dict, Optional
from src.type_formatter import TypeFormatter


class AbstainGate:
  """Inspects answers and execution context to decide whether to submit or abstain."""

  @classmethod
  def should_abstain(
      cls,
      answer_obj: Dict[str, Any],
      question_text: str = '',
      exec_history: Optional[list] = None
  ) -> bool:
    """Check if the answer should be converted to abstain to protect total score."""
    ans_type = answer_obj.get('type')

    if ans_type == 'abstain':
      return True

    if ans_type == 'unanswerable':
      # Unanswerable has reason, valid to submit
      return False

    val = answer_obj.get('answer')
    if val is None:
      return True

    q_lower = question_text.lower()

    # 1. Number checks
    if ans_type == 'number':
      if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
        return True
      # Revenue, sales count, order count cannot be negative
      if val < 0 and any(w in q_lower for w in ['doanh thu', 'dthu', 'số đơn', 'bao nhiêu đơn', 'mấy đơn', 'số ly', 'số lượng']):
        return True

    # 2. Percent checks
    elif ans_type == 'percent':
      if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
        return True

    # 3. String checks
    elif ans_type == 'string':
      if not isinstance(val, str) or not val.strip():
        return True
      # Discard hallucinations or error messages
      if any(err_word in val.lower() for err_word in ['syntaxerror', 'traceback', 'exception', 'none', 'null', 'không rõ']):
        return True

    # 4. List checks
    elif ans_type == 'list':
      if not isinstance(val, list) or len(val) == 0:
        return True

    # 5. Table checks
    elif ans_type == 'table':
      if not isinstance(val, dict):
        return True
      cols = val.get('columns', [])
      rows = val.get('rows', [])
      if not cols or not rows:
        return True

    # 6. Boolean checks
    elif ans_type == 'boolean':
      if not isinstance(val, bool):
        return True

    return False

  @classmethod
  def filter_answer(
      cls,
      answer_obj: Dict[str, Any],
      question_text: str = '',
      exec_history: Optional[list] = None
  ) -> Dict[str, Any]:
    """Apply strict formatting and risk filtering. Returns safe submission dict."""
    formatted = TypeFormatter.format_answer_object(answer_obj, question_text=question_text)
    qid = formatted.get('id', answer_obj.get('id', ''))

    if cls.should_abstain(formatted, question_text, exec_history):
      return {'id': qid, 'type': 'abstain'} if qid else {'type': 'abstain'}

    return formatted
