"""Reasoning Agent and Pipeline Module for Zalo AI DataMate.

Orchestrates the entire Code-as-Reasoning workflow:
Data Ingestion -> Schema Profiling -> Temporal Anchoring -> Prompt Generation ->
LLM Code Generation -> Sandbox Execution -> Self-Reflection Loop -> Abstain
Fallback.
"""

from abc import ABC, abstractmethod
from datetime import datetime
import json
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import duckdb
from src.abstain_gate import AbstainGate
from src.calendar_resolver import CalendarResolver
from src.data_ingestor import DataIngestor
from src.llm_client import BaseLLMClient, MockLLMClient, OllamaClient, OpenAICompatibleClient
from src.prompt_generator import PromptGenerator
from src.query_normalizer import QueryNormalizer
from src.rulebook_parser import RulebookParser
from src.sandbox import ExecutionSandbox
from src.schema_profiler import SchemaProfiler


# Alias for backward compatibility
LLMClient = BaseLLMClient


def extract_python_code(text: str) -> str:
  """Extract Python code block from markdown response."""
  # Look for ```python ... ```
  pattern = r'```(?:python)?\s*(.*?)\s*```'
  matches = re.findall(pattern, text, flags=re.DOTALL)
  if matches:
    # Prefer the longest block or the one containing 'def solve'
    for m in matches:
      if 'def solve' in m:
        return m.strip()
    return matches[-1].strip()

  # If no markdown fences, check if raw code contains def solve
  if 'def solve' in text:
    return text.strip()

  return text.strip()


class ReasoningPipeline:
  """Main Reasoning Pipeline for Vietnamese SME Question Answering."""

  def __init__(
      self,
      rulebook_path: Path,
      calendar_path: Path,
      llm_client: LLMClient,
      sandbox_timeout: float = 10.0,
      max_retries: int = 2,
  ):
    self.rulebook_path = rulebook_path
    self.calendar_path = calendar_path
    self.rulebook_parser = RulebookParser(rulebook_path)
    self.calendar_resolver = CalendarResolver(calendar_path)
    self.query_normalizer = QueryNormalizer(self.calendar_resolver)
    self.llm_client = llm_client
    self.sandbox = ExecutionSandbox(timeout_sec=sandbox_timeout)
    self.max_retries = max_retries

    # Cache for ingested businesses: {biz_id: (ingestor, profiler)}
    self.biz_cache: Dict[str, Tuple[DataIngestor, SchemaProfiler]] = {}

  def get_or_ingest_biz(self, biz_dir: Path) -> Tuple[DataIngestor, SchemaProfiler]:
    biz_id = biz_dir.name
    if biz_id not in self.biz_cache:
      ingestor = DataIngestor(':memory:')
      ingestor.ingest_business(biz_dir, calendar_path=self.calendar_path)
      profiler = SchemaProfiler(ingestor, biz_dir)
      self.biz_cache[biz_id] = (ingestor, profiler)
    return self.biz_cache[biz_id]

  def solve_question(
      self,
      question_obj: Dict[str, Any],
      biz_dir: Path,
      log_dir: Optional[Path] = None,
  ) -> Dict[str, Any]:
    """Execute complete reasoning pipeline for a single question record."""
    start_time = time.perf_counter()
    qid = question_obj['id']
    q_text = question_obj['question']
    as_of = question_obj.get('as_of_date', '2026-08-27')

    ingestor, profiler = self.get_or_ingest_biz(biz_dir)

    # 1. Temporal bounds extraction
    temporal_anchors = self.query_normalizer.extract_temporal_bounds(
        q_text, as_of
    )

    # 2. Rule 7 check: Out of range detection
    min_d, max_d = profiler.get_overall_date_bounds()
    if min_d and max_d and temporal_anchors.get('primary_window'):
      s, e = temporal_anchors['primary_window']
      # If asked period is strictly before min_date or strictly after max_date
      if e < min_d or s > max_d:
        elapsed = time.perf_counter() - start_time
        final_answer = {
            'id': qid,
            'type': 'unanswerable',
            'reason': (
                f'Kỳ hỏi ({s} đến {e}) nằm hoàn toàn ngoài khoảng ngày có dữ'
                f' liệu ({min_d} đến {max_d})'
            ),
        }
        self._write_log(
            log_dir,
            qid,
            final_answer,
            elapsed,
            'Rule 7 Out-of-range pre-check',
        )
        return final_answer

    # 3. Generate master prompt
    schema_ctx = profiler.to_prompt_context()
    rules_ctx = self.rulebook_parser.get_rule_summary_for_prompt(
        q_text, profiler.readme_text
    )
    prompt = PromptGenerator.generate_prompt(
        question=q_text,
        as_of_date=as_of,
        schema_context=schema_ctx,
        rules_summary=rules_ctx,
        temporal_anchors=temporal_anchors,
        available_tables=list(profiler.table_profiles.keys()),
        table_profiles=profiler.table_profiles,
    )

    history_logs = []
    current_prompt = prompt
    final_result = None

    # 4. Code Generation & Sandbox Reflection Loop
    for attempt in range(self.max_retries + 1):
      llm_response = self.llm_client.generate(current_prompt)
      code_str = extract_python_code(llm_response)

      exec_res = self.sandbox.execute_code(code_str, ingestor.con, as_of_date=as_of)
      history_logs.append({
          'attempt': attempt + 1,
          'code': code_str,
          'exec_success': exec_res['success'],
          'exec_result': exec_res['result'],
          'exec_error': exec_res['error'],
          'elapsed_sec': exec_res['elapsed_sec'],
      })

      if exec_res['success'] and isinstance(exec_res['result'], dict):
        # Successfully returned answer dict
        final_result = exec_res['result']
        break
      else:
        # Prepare reflection prompt for next attempt
        err_msg = exec_res['error'] or 'Code did not return a valid dictionary.'
        current_prompt = PromptGenerator.generate_reflection_prompt(
            original_prompt=prompt, previous_code=code_str, error_message=err_msg
        )

    # 5. Fallback Decision & Strict Formatting via AbstainGate
    elapsed = time.perf_counter() - start_time
    if final_result and 'type' in final_result:
      raw_answer = {'id': qid, **final_result}
    else:
      raw_answer = {
          'id': qid,
          'type': 'abstain',
          'reason': 'Execution failed after retries',
      }

    final_answer = AbstainGate.filter_answer(
        raw_answer, question_text=q_text, exec_history=history_logs
    )

    self._write_log(
        log_dir, qid, final_answer, elapsed, history_logs, original_prompt=prompt
    )
    return final_answer

  def _write_log(
      self,
      log_dir: Optional[Path],
      qid: str,
      final_answer: Dict[str, Any],
      elapsed: float,
      trace: Any,
      original_prompt: str = '',
  ):
    if not log_dir:
      return
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f'{qid}.json'
    log_data = {
        'id': qid,
        'final_answer': final_answer,
        'elapsed_seconds': round(elapsed, 4),
        'trace': trace,
        'original_prompt': original_prompt,
    }
    with open(log_file, 'w', encoding='utf-8') as f:
      json.dump(log_data, f, ensure_ascii=False, indent=2)
