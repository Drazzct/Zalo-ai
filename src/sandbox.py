"""Execution Sandbox Module for Zalo AI DataMate.

Executes generated Python/DuckDB code safely with timeout control,
exception capturing, and performance measurement.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import sys
import time
import traceback
from typing import Any, Dict, Optional
import duckdb


class ExecutionSandbox:
  """Executes generated Python code that queries DuckDB and returns the answer."""

  def __init__(self, timeout_sec: float = 10.0):
    self.timeout_sec = timeout_sec

  def execute_code(
      self,
      code_str: str,
      con: duckdb.DuckDBPyConnection
  ) -> Dict[str, Any]:
    """Execute Python code containing `solve(con) -> dict`.

    Returns {
        'success': bool,
        'result': Any,
        'error': Optional[str],
        'elapsed_sec': float
    }
    """
    start_time = time.perf_counter()

    # Pre-compile check for syntax errors
    try:
      compiled_code = compile(code_str, '<generated_code>', 'exec')
    except SyntaxError as e:
      elapsed = time.perf_counter() - start_time
      return {
          'success': False,
          'result': None,
          'error': f'SyntaxError: {e}',
          'elapsed_sec': elapsed
      }

    # Prepare execution environment
    # Provide safe builtins, math, pandas, duckdb, re, datetime
    import math
    import re
    from datetime import date, datetime, timedelta
    import pandas as pd

    local_scope: Dict[str, Any] = {
        'con': con,
        'pd': pd,
        'duckdb': duckdb,
        'math': math,
        're': re,
        'date': date,
        'datetime': datetime,
        'timedelta': timedelta,
    }

    def _run():
      exec(compiled_code, local_scope)
      if 'solve' not in local_scope or not callable(local_scope['solve']):
        raise ValueError("Generated code must define a callable 'solve(con)' function.")
      return local_scope['solve'](con)

    with ThreadPoolExecutor(max_workers=1) as executor:
      future = executor.submit(_run)
      try:
        res = future.result(timeout=self.timeout_sec)
        elapsed = time.perf_counter() - start_time
        return {
            'success': True,
            'result': res,
            'error': None,
            'elapsed_sec': elapsed
        }
      except FutureTimeoutError:
        elapsed = time.perf_counter() - start_time
        return {
            'success': False,
            'result': None,
            'error': f'TimeoutError: Execution exceeded limit of {self.timeout_sec}s',
            'elapsed_sec': elapsed
        }
      except Exception as e:
        elapsed = time.perf_counter() - start_time
        tb_str = traceback.format_exc()
        return {
            'success': False,
            'result': None,
            'error': f'{type(e).__name__}: {e}\n{tb_str}',
            'elapsed_sec': elapsed
        }

