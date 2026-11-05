"""Unit tests for Phase 1 components:

CalendarResolver, RulebookParser, and Evaluator.
"""

from datetime import date
from pathlib import Path
import pytest
from src.calendar_resolver import CalendarResolver
from src.evaluator import Evaluator
from src.rulebook_parser import RulebookParser


@pytest.fixture
def calendar_resolver():
  return CalendarResolver(Path('train/calendar.csv'))


@pytest.fixture
def train_rulebook():
  return RulebookParser(Path('train/rulebook.md'))


@pytest.fixture
def public_test_rulebook():
  return RulebookParser(Path('public_test/rulebook.md'))


class TestCalendarResolver:

  def test_tet_window_2025(self, calendar_resolver):
    # Tết 2025: 23 Chạp Giáp Thìn (2025-01-22) to mùng 10 Ất Tỵ (2025-02-07)
    start_tet, end_tet = calendar_resolver.get_tet_window(2025)
    assert start_tet == date(2025, 1, 22)
    assert end_tet == date(2025, 2, 7)

  def test_week_window(self, calendar_resolver):
    # 2026-08-27 is Thursday (weekday 3)
    as_of = date(2026, 8, 27)
    start_w, end_w = calendar_resolver.get_week_window(as_of, 'this_week')
    # Monday of that week: 2026-08-24
    assert start_w == date(2026, 8, 24)
    assert end_w == date(2026, 8, 27)

    # Previous week: Monday 2026-08-17 to Sunday 2026-08-23
    prev_start, prev_end = calendar_resolver.get_week_window(as_of, 'prev_week')
    assert prev_start == date(2026, 8, 17)
    assert prev_end == date(2026, 8, 23)

  def test_month_window(self, calendar_resolver):
    as_of = date(2026, 8, 27)
    start_m, end_m = calendar_resolver.get_month_window(as_of, 'this_month')
    assert start_m == date(2026, 8, 1)
    assert end_m == date(2026, 8, 27)

    # Same period last month: July has 31 days, so 2026-07-01 to 2026-07-27
    last_m_start, last_m_end = calendar_resolver.get_month_window(
        as_of, 'same_period_last_month'
    )
    assert last_m_start == date(2026, 7, 1)
    assert last_m_end == date(2026, 7, 27)


class TestRulebookParser:

  def test_train_sections(self, train_rulebook):
    assert len(train_rulebook.sections) >= 8
    assert any('Đơn hàng và doanh thu' in s for s in train_rulebook.sections)

  def test_industry_rules_extraction(
      self, train_rulebook, public_test_rulebook
  ):
    # Train industries: Cà phê, Nhà thuốc, Vật liệu xây dựng
    train_inds = train_rulebook.get_available_industries()
    assert 'Cà phê' in train_inds
    assert 'Nhà thuốc' in train_inds
    assert 'Vật liệu xây dựng' in train_inds

    # Public test has new industries!
    test_inds = public_test_rulebook.get_available_industries()
    assert 'Mẹ và bé' in test_inds
    assert 'Sửa xe' in test_inds
    assert 'Cửa hàng điện thoại' in test_inds

  def test_detect_industry(self, train_rulebook, public_test_rulebook):
    assert (
        train_rulebook.detect_industry('Hôm nay bán được bao nhiêu ly Cà phê?')
        == 'Cà phê'
    )
    assert (
        train_rulebook.detect_industry('Thuốc kê đơn nào bán chạy nhất?')
        == 'Nhà thuốc'
    )
    assert (
        public_test_rulebook.detect_industry(
            'Có bao nhiêu lượt xe sửa ruột và thay nhớt?'
        )
        == 'Sửa xe'
    )
    assert (
        public_test_rulebook.detect_industry('Doanh số bỉm tã size M tháng này')
        == 'Mẹ và bé'
    )


class TestEvaluator:

  def test_number_matching(self):
    assert Evaluator.match_number(4820000, 4820000)
    assert Evaluator.match_number('4820000', 4820000)
    assert Evaluator.match_number(18.5001, 18.5)
    assert not Evaluator.match_number(4820001, 4820000)

  def test_percent_matching(self):
    assert Evaluator.match_percent(-12.45, -12.45)
    assert Evaluator.match_percent('-12.45', -12.45)
    assert Evaluator.match_percent(12.40, 12.4)
    assert not Evaluator.match_percent(12.45, 12.50)

  def test_string_and_alias_matching(self):
    gt = 'Xi măng Hà Tiên PCB40 bao 50kg'
    aliases = ['SP0001', 'Xi măng Hà Tiên 50kg']
    # Exact match
    assert Evaluator.match_string('Xi măng Hà Tiên PCB40 bao 50kg', gt, aliases)
    # Case & space insensitive
    assert Evaluator.match_string(
        '  xi măng hà tiên pcb40 bao 50kg  ', gt, aliases
    )
    # Alias match
    assert Evaluator.match_string('SP0001', gt, aliases)
    assert Evaluator.match_string('sp0001', gt, aliases)
    assert not Evaluator.match_string('Xi măng Nghi Sơn', gt, aliases)

  def test_list_matching(self):
    gt = ['Cà phê sữa', 'Bạc xỉu', 'Trà đào']
    assert Evaluator.match_list(['Cà phê sữa', 'Bạc xỉu', 'Trà đào'], gt)
    # Order matters!
    assert not Evaluator.match_list(['Bạc xỉu', 'Cà phê sữa', 'Trà đào'], gt)
    assert not Evaluator.match_list(['Cà phê sữa'], gt)

  def test_table_matching(self):
    gt = {
        'columns': ['khach_hang', 'so_tien_no'],
        'rows': [['Chị Lan', 3200000], ['Anh Tú', 1500000]],
    }
    # Same rows, different row order -> Still valid according to Rule 137
    pred = {
        'columns': ['khach_hang', 'so_tien_no'],
        'rows': [['Anh Tú', 1500000], ['Chị Lan', 3200000]],
    }
    assert Evaluator.match_table(pred, gt)

  def test_score_calculation(self):
    gt = [
        {'id': 'q1', 'type': 'number', 'answer': 100},
        {'id': 'q2', 'type': 'string', 'answer': 'Sting dâu'},
        {'id': 'q3', 'type': 'unanswerable', 'answer': None},
        {'id': 'q4', 'type': 'boolean', 'answer': True},
    ]

    preds = [
        {'id': 'q1', 'type': 'number', 'answer': 100},  # Correct: +1
        {'id': 'q2', 'type': 'string', 'answer': 'Pepsi'},  # Wrong: -1
        {'id': 'q3', 'type': 'unanswerable', 'reason': 'No data'},  # Correct: +1
        {'id': 'q4', 'type': 'abstain'},  # Abstain: 0
    ]

    res = Evaluator.evaluate(preds, gt)
    assert res['correct'] == 2
    assert res['wrong'] == 1
    assert res['abstain'] == 1
    assert res['total_score'] == 1  # 2 - 1 = 1

