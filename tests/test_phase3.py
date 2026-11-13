"""Unit and Integration tests for Phase 3:

QueryNormalizer, ExecutionSandbox, PromptGenerator, and ReasoningPipeline.
"""

from pathlib import Path
import tempfile
import time
import pytest
from src.agent_pipeline import MockLLMClient, ReasoningPipeline, extract_python_code, extract_reasoning
from src.calendar_resolver import CalendarResolver
from src.data_ingestor import DataIngestor
from src.prompt_generator import PromptGenerator
from src.query_normalizer import QueryNormalizer
from src.sandbox import ExecutionSandbox


@pytest.fixture
def calendar_resolver():
  return CalendarResolver(Path('train/calendar.csv'))


@pytest.fixture
def query_normalizer(calendar_resolver):
  return QueryNormalizer(calendar_resolver)


class TestQueryNormalizer:

  def test_teencode_normalization(self, query_normalizer):
    raw = 'check gium dthu hnay cua shop la bnhiu z'
    norm = query_normalizer.normalize_text(raw)
    assert 'giúp' in norm
    assert 'doanh thu' in norm
    assert 'hôm nay' in norm
    assert 'bao nhiêu' in norm

  def test_temporal_bounds_extraction(self, query_normalizer):
    as_of = '2026-08-27'  # Thursday
    # 1. Hôm nay
    t1 = query_normalizer.extract_temporal_bounds(
        'Tổng doanh thu hôm nay là bao nhiêu?', as_of
    )
    assert t1['primary_window'] == ('2026-08-27', '2026-08-27')

    # 2. Tháng này
    t2 = query_normalizer.extract_temporal_bounds(
        'Tháng này bán được bao nhiêu tiền?', as_of
    )
    assert t2['primary_window'] == ('2026-08-01', '2026-08-27')

    # 3. Tuần này (Monday to as_of)
    t3 = query_normalizer.extract_temporal_bounds(
        'Hàng nào bán chạy nhất tuần này?', as_of
    )
    assert t3['primary_window'] == ('2026-08-24', '2026-08-27')

    # 4. Tháng 6/2025
    t4 = query_normalizer.extract_temporal_bounds(
        'Tỉ lệ huỷ đơn tháng 6/2025 là bao nhiêu %?', as_of
    )
    assert t4['primary_window'] == ('2025-06-01', '2025-06-30')


class TestExecutionSandbox:

  def test_valid_code_execution(self):
    ingestor = DataIngestor(':memory:')
    ingestor.con.execute(
        'CREATE TABLE test_table (id INT, amount DOUBLE); INSERT INTO'
        ' test_table VALUES (1, 50000), (2, 30000);'
    )
    sandbox = ExecutionSandbox(timeout_sec=5.0)

    code = """
def solve(con):
    total = con.execute("SELECT SUM(amount) FROM test_table").fetchone()[0]
    return {"type": "number", "answer": int(total)}
"""
    res = sandbox.execute_code(code, ingestor.con)
    assert res['success'] is True
    assert res['result'] == {'type': 'number', 'answer': 80000}
    assert res['error'] is None
    ingestor.close()

  def test_syntax_error_handling(self):
    ingestor = DataIngestor(':memory:')
    sandbox = ExecutionSandbox(timeout_sec=5.0)
    code = 'def solve(con):\n    return {"type": "number", missing_bracket'
    res = sandbox.execute_code(code, ingestor.con)
    assert res['success'] is False
    assert 'SyntaxError' in res['error']
    ingestor.close()

  def test_timeout_handling(self):
    ingestor = DataIngestor(':memory:')
    sandbox = ExecutionSandbox(timeout_sec=0.5)
    code = """
import time
def solve(con):
    time.sleep(1.0)
    return {"type": "boolean", "answer": True}
"""
    res = sandbox.execute_code(code, ingestor.con)
    assert res['success'] is False
    assert 'TimeoutError' in res['error']
    ingestor.close()


class TestReasoningPipeline:

  def test_rule7_unanswerable_detection(self):
    pipeline = ReasoningPipeline(
        rulebook_path=Path('train/rulebook.md'),
        calendar_path=Path('train/calendar.csv'),
        llm_client=MockLLMClient(),
    )
    # Question asks for Feb 2025 on biz_121, but data starts in March 2025
    q_obj = {
        'id': 'q_test_rule7',
        'question': 'trong thang 2/2025, ti le don huy la bao nhieu %',
        'as_of_date': '2026-09-20',
    }
    ans = pipeline.solve_question(q_obj, Path('train/data/biz_121'))
    assert ans['type'] == 'unanswerable'
    assert 'ngoài khoảng ngày' in ans['reason']

  def test_e2e_solving_with_mock_llm(self):
    # Canned response for biz_101 question: revenue on 2025-06-01
    canned = {
        '2025-06-01': """```python
def solve(con):
    # Query revenue on 2025-06-01
    res = con.execute("SELECT SUM(thanh_tien) FROM ban_hang WHERE ngay_thang = '2025-06-01'").fetchone()[0]
    return {
        "type": "number",
        "answer": int(round(res))
    }
```"""
    }
    client = MockLLMClient(canned_responses=canned)
    pipeline = ReasoningPipeline(
        rulebook_path=Path('train/rulebook.md'),
        calendar_path=Path('train/calendar.csv'),
        llm_client=client,
    )

    q_obj = {
        'id': 'q_test_biz101',
        'question': 'Tổng doanh thu ngày 01/06/2025 là bao nhiêu?',
        'as_of_date': '2025-06-02',
    }
    with tempfile.TemporaryDirectory() as tmpdir:
      ans = pipeline.solve_question(
          q_obj, Path('train/data/biz_101'), log_dir=Path(tmpdir)
      )
      assert ans['type'] == 'number'
      assert ans['answer'] > 0
      # Verify log was written
      log_file = Path(tmpdir) / 'q_test_biz101.json'
      assert log_file.exists()

  def test_reflection_and_abstain_fallback(self):
    # Client that fails first attempt with syntax error, succeeds on second attempt
    class ReflectiveClient(MockLLMClient):

      def __init__(self):
        super().__init__()
        self.call_count = 0

      def generate(self, prompt: str) -> str:
        self.call_count += 1
        if self.call_count == 1:
          # First attempt has syntax error
          return 'def solve(con):\n    return error'
        else:
          # Second attempt fixes it
          return """```python
def solve(con):
    return {"type": "boolean", "answer": True}
```"""

    ref_client = ReflectiveClient()
    pipeline = ReasoningPipeline(
        rulebook_path=Path('train/rulebook.md'),
        calendar_path=Path('train/calendar.csv'),
        llm_client=ref_client,
        max_retries=2,
    )
    q_obj = {
        'id': 'q_test_reflection',
        'question': 'Cửa hàng có mở cửa không?',
        'as_of_date': '2026-08-27',
    }
    ans = pipeline.solve_question(q_obj, Path('train/data/biz_101'))
    assert ans['type'] == 'boolean'
    assert ans['answer'] is True
    assert ref_client.call_count == 2

  def test_extract_reasoning_and_prompt(self):
    sample_llm_output = """<reasoning>
1. Câu hỏi yêu cầu tính doanh thu ngày hôm nay (2026-08-27).
2. Dùng bảng ban_hang, cột ngay_ban và thanh_tien.
3. Loại bỏ đơn hủy hoặc hoàn trả.
</reasoning>

```python
def solve(con):
    res = con.execute("SELECT SUM(thanh_tien) FROM ban_hang").fetchone()[0]
    return {"type": "number", "answer": int(res)}
```"""
    reasoning = extract_reasoning(sample_llm_output)
    code = extract_python_code(sample_llm_output)

    assert "Câu hỏi yêu cầu tính doanh thu" in reasoning
    assert "def solve(con):" in code
    assert "<reasoning>" not in code

    # Test prompt generation with reasoning
    prompt = PromptGenerator.generate_prompt(
        question="Doanh thu hôm nay?",
        as_of_date="2026-08-27",
        schema_context="CREATE TABLE ban_hang ...",
        rules_summary="Rule 1: ...",
        temporal_anchors={},
        enable_reasoning=True,
    )
    assert "<reasoning>" in prompt
    assert "HƯỚNG DẪN SUY LUẬN TỪNG BƯỚC" in prompt


