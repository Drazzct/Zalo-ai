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


class DuckDBContextWrapper:
  """Wrapper around DuckDBPyConnection to support both SQL execution and dictionary indexing for pandas."""

  def __init__(self, con: duckdb.DuckDBPyConnection, as_of_date: str = ''):
    self._con = con
    self.as_of_date = as_of_date
    self._df_cache = {}

  def execute(self, query: str, *args, **kwargs):
    return self._con.execute(query, *args, **kwargs)

  def fetchall(self):
    return self._con.fetchall()

  def fetchone(self):
    return self._con.fetchone()

  def __getitem__(self, key: str):
    if key == 'as_of_date':
      return self.as_of_date
    if key not in self._df_cache:
      try:
        self._df_cache[key] = self._con.execute(f'SELECT * FROM "{key}"').df()
      except Exception:
        res = self._con.execute(
            f"SELECT table_name FROM information_schema.tables WHERE LOWER(table_name) = '{key.lower()}'"
        ).fetchone()
        if res:
          self._df_cache[key] = self._con.execute(f'SELECT * FROM "{res[0]}"').df()
        else:
          raise KeyError(f"Table '{key}' not found in database.")
    return self._df_cache[key]

  def get(self, key: str, default=None):
    try:
      return self[key]
    except (KeyError, Exception):
      return default

  def keys(self):
    tables = [
        r[0]
        for r in self._con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
    ]
    return ['as_of_date'] + tables

  def __contains__(self, key: str) -> bool:
    if key == 'as_of_date':
      return True
    try:
      self[key]
      return True
    except Exception:
      return False

  def __getattr__(self, name: str):
    return getattr(self._con, name)


class ExecutionSandbox:
  """Executes generated Python code that queries DuckDB and returns the answer."""

  def __init__(self, timeout_sec: float = 10.0):
    self.timeout_sec = timeout_sec

  def execute_code(
      self,
      code_str: str,
      con: duckdb.DuckDBPyConnection,
      as_of_date: str = ''
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

    wrapped_con = DuckDBContextWrapper(con, as_of_date=as_of_date) if not isinstance(con, DuckDBContextWrapper) else con

    local_scope: Dict[str, Any] = {
        'con': wrapped_con,
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
      raw_res = local_scope['solve'](wrapped_con)
      # Auto-wrap primitive return values if not returned as a dictionary
      if not isinstance(raw_res, dict):
        if isinstance(raw_res, bool):
          return {'type': 'boolean', 'answer': raw_res}
        elif isinstance(raw_res, (int, float)):
          return {'type': 'number', 'answer': raw_res}
        elif isinstance(raw_res, str):
          return {'type': 'string', 'answer': raw_res}
        elif isinstance(raw_res, list):
          return {'type': 'list', 'answer': raw_res}
      return raw_res

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

