"""Unit tests for Phase 4:

TypeFormatter, AbstainGate, and Benchmark Integration.
"""

from pathlib import Path
import pytest
from src.abstain_gate import AbstainGate
from src.type_formatter import TypeFormatter


class TestTypeFormatter:

  def test_format_number(self):
    assert TypeFormatter.format_number('4,820,000') == 4820000
    assert TypeFormatter.format_number('4.820.000đ', is_money_or_count=True) == 4820000
    assert TypeFormatter.format_number('18.6') == 18.6
    assert TypeFormatter.format_number(None) is None

  def test_format_percent(self):
    assert TypeFormatter.format_percent('12.45%') == 12.45
    assert TypeFormatter.format_percent('-5.2%') == -5.20
    assert TypeFormatter.format_percent(12.4) == 12.40
    assert TypeFormatter.format_percent(None) is None

  def test_format_date(self):
    assert TypeFormatter.format_date('15/08/2026') == '2026-08-15'
    assert TypeFormatter.format_date('2025-09') == '2025-09'
    assert TypeFormatter.format_date('2026-08-15 14:00:00') == '2026-08-15'

  def test_format_boolean(self):
    assert TypeFormatter.format_boolean('có') is True
    assert TypeFormatter.format_boolean('đúng') is True
    assert TypeFormatter.format_boolean('không') is False
    assert TypeFormatter.format_boolean('sai') is False
    assert TypeFormatter.format_boolean(True) is True

  def test_format_string(self):
    assert TypeFormatter.format_string('  Sting dâu 330ml  ') == 'Sting dâu 330ml'
    assert TypeFormatter.format_string(['Sting dâu 330ml']) == 'Sting dâu 330ml'
    assert TypeFormatter.format_string('') is None

  def test_format_list(self):
    assert TypeFormatter.format_list('Cà phê sữa, Bạc xỉu') == ['Cà phê sữa', 'Bạc xỉu']
    assert TypeFormatter.format_list(['3', '10']) == [3, 10]
    assert TypeFormatter.format_list('Đơn chiếc') == ['Đơn chiếc']

  def test_format_table(self):
    raw_tbl = {
        'columns': ['khach_hang', 'so_tien_no'],
        'rows': [['Chị Lan', '3.200.000đ'], ['Anh Tú', '1.500.000']],
    }
    fmt = TypeFormatter.format_table(raw_tbl)
    assert fmt['columns'] == ['khach_hang', 'so_tien_no']
    assert fmt['rows'] == [['Chị Lan', 3200000], ['Anh Tú', 1500000]]


class TestAbstainGate:

  def test_abstain_on_negative_revenue(self):
    # Revenue cannot be negative
    ans = {'type': 'number', 'answer': -500000}
    filtered = AbstainGate.filter_answer(
        ans, question_text='Tổng doanh thu tháng 5 là bao nhiêu?'
    )
    assert filtered['type'] == 'abstain'

  def test_allow_negative_growth_percent(self):
    # Percentage growth CAN be negative
    ans = {'type': 'percent', 'answer': -12.45}
    filtered = AbstainGate.filter_answer(
        ans, question_text='Doanh thu tháng này tăng trưởng bao nhiêu %?'
    )
    assert filtered['type'] == 'percent'
    assert filtered['answer'] == -12.45

  def test_abstain_on_error_string(self):
    ans = {'type': 'string', 'answer': 'Error: syntaxerror in table'}
    filtered = AbstainGate.filter_answer(ans)
    assert filtered['type'] == 'abstain'

  def test_abstain_on_empty_list(self):
    ans = {'type': 'list', 'answer': []}
    filtered = AbstainGate.filter_answer(
        ans, question_text='Top 3 mặt hàng bán chạy'
    )
    assert filtered['type'] == 'abstain'

