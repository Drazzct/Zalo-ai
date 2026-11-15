"""Main prediction entry point for Zalo AI DataMate.

Complies directly with the competition Docker specification:
Reads test set from --input-dir (default: /data) and writes output to --output
(default: /result/submission.jsonl)
along with per-question logs to --log-dir (default: /result/logs).
"""

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import sys
import threading
import time

# Ensure UTF-8 output on Windows / Linux
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
  sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
  sys.stderr.reconfigure(encoding='utf-8')

from src.agent_pipeline import ReasoningPipeline
from src.llm_client import MockLLMClient, OllamaClient, OpenAICompatibleClient


def load_jsonl(path: Path):
  records = []
  with open(path, encoding='utf-8') as f:
    for line in f:
      if line.strip():
        records.append(json.loads(line))
  return records


def main():
  parser = argparse.ArgumentParser(
      description='Run DataMate inference for Zalo AI competition.'
  )
  parser.add_argument(
      '--input-dir',
      type=str,
      default=os.environ.get('DATA_DIR', '/data' if Path('/data').exists() else 'public_test'),
      help='Path to input split folder containing questions.jsonl, rulebook.md, calendar.csv, data/',
  )
  parser.add_argument(
      '--output',
      type=str,
      default=os.environ.get('OUTPUT_FILE', '/result/submission.jsonl' if Path('/result').exists() else 'submission.jsonl'),
      help='Path to output submission.jsonl',
  )
  parser.add_argument(
      '--log-dir',
      type=str,
      default=os.environ.get('LOG_DIR', '/result/logs' if Path('/result').exists() else 'result/logs'),
      help='Path to directory for per-question logs',
  )
  parser.add_argument(
      '--limit',
      type=int,
      default=None,
      help='Limit number of questions to process',
  )
  parser.add_argument(
      '--model-backend',
      type=str,
      choices=['mock', 'ollama', 'vllm'],
      default=os.environ.get('MODEL_BACKEND', 'ollama'),
      help='LLM backend to use for code generation (default: ollama)',
  )
  parser.add_argument(
      '--model-name',
      type=str,
      default=os.environ.get('MODEL_NAME', 'qwen3.5:9b'),
      help='Model name (e.g. qwen3.5:9b, qwen2.5-coder:7b)',
  )
  parser.add_argument(
      '--api-url',
      type=str,
      default=os.environ.get('API_URL', 'http://127.0.0.1:11434'),
      help='URL of Ollama or vLLM server',
  )
  parser.add_argument(
      '--workers',
      type=int,
      default=int(os.environ.get('NUM_WORKERS', '2')),
      help='Number of parallel worker threads (default: 2)',
  )
  parser.add_argument(
      '--no-reasoning',
      action='store_true',
      help='Disable step-by-step reasoning in prompt',
  )
  parser.add_argument(
      '--resume',
      action='store_true',
      help='Resume from existing submission file (skip already answered questions)',
  )

  args = parser.parse_args()
  input_path = Path(args.input_dir)
  out_path = Path(args.output)
  log_path = Path(args.log_dir)

  q_file = input_path / 'questions.jsonl'
  rb_file = input_path / 'rulebook.md'
  cal_file = input_path / 'calendar.csv'
  data_dir = input_path / 'data'

  if not q_file.exists():
    print(f'Error: Questions file not found at {q_file}')
    sys.exit(1)

  out_path.parent.mkdir(parents=True, exist_ok=True)
  log_path.mkdir(parents=True, exist_ok=True)

  # Model selection
  if args.model_backend == 'mock':
    llm_client = MockLLMClient()
  elif args.model_backend == 'ollama':
    llm_client = OllamaClient(model_name=args.model_name, host=args.api_url)
  elif args.model_backend == 'vllm':
    llm_client = OpenAICompatibleClient(model_name=args.model_name, base_url=args.api_url)
  else:
    llm_client = MockLLMClient()

  enable_reasoning = not args.no_reasoning
  pipeline = ReasoningPipeline(
      rulebook_path=rb_file,
      calendar_path=cal_file,
      llm_client=llm_client,
      sandbox_timeout=10.0,
      max_retries=2,
      enable_reasoning=enable_reasoning,
  )

  questions = load_jsonl(q_file)
  if args.limit:
    questions = questions[: args.limit]

  answered_ids = set()
  if args.resume and out_path.exists():
    with open(out_path, 'r', encoding='utf-8') as f:
      for line in f:
        line_s = line.strip()
        if line_s:
          try:
            it = json.loads(line_s)
            if 'id' in it:
              answered_ids.add(it['id'])
          except Exception:
            pass
    if answered_ids:
      print(f'⚡ RESUME MODE: Found {len(answered_ids)} answered questions in {out_path.name}.')
      questions = [q for q in questions if q['id'] not in answered_ids]
      print(f'Remaining questions to solve: {len(questions)}')

  if not questions:
    print('All questions have already been answered! Nothing to do.')
    return

  # Pre-warm business database caches into in-memory DuckDB
  unique_biz = {q['business_id'] for q in questions}
  print(f'Pre-warming DuckDB in-memory cache for {len(unique_biz)} businesses...')
  for b_id in sorted(unique_biz):
    b_dir = data_dir / b_id
    if b_dir.exists():
      try:
        pipeline.get_or_ingest_biz(b_dir)
      except Exception as e:
        print(f'Warning: Could not pre-cache {b_id}: {e}')
  print('✅ Business databases loaded into memory.')

  print('=' * 60)
  print('ZALO AI DATAMATE - PREDICTION RUNNER')
  print(f'Input Directory  : {input_path.resolve()}')
  print(f'Total Questions  : {len(questions)}')
  print(f'Output File      : {out_path.resolve()}')
  print(f'Log Directory    : {log_path.resolve()}')
  print(f'Backend          : {args.model_backend} ({args.model_name})')
  print(f'Workers          : {args.workers}')
  print(f'Reasoning Mode   : {enable_reasoning}')
  print('=' * 60)

  start_all = time.perf_counter()

  open_mode = 'a' if (args.resume and out_path.exists()) else 'w'
  if open_mode == 'w':
    with open(out_path, 'w', encoding='utf-8') as out_f:
      pass

  if args.workers <= 1:
    with open(out_path, 'a', encoding='utf-8') as out_f:
      for i, q in enumerate(questions):
        biz_id = q['business_id']
        biz_dir = data_dir / biz_id

        ans_obj = pipeline.solve_question(q, biz_dir, log_dir=log_path)
        line = json.dumps(ans_obj, ensure_ascii=False)
        out_f.write(line + '\n')
        out_f.flush()

        ans_prev = f"type={ans_obj.get('type')}, answer={ans_obj.get('answer', ans_obj.get('reason'))}"
        print(f"[{i + 1}/{len(questions)}] {q['id']} ({biz_id}) -> {ans_prev}", flush=True)
  else:
    write_lock = threading.Lock()

    def _worker(item):
      idx, q = item
      biz_id = q['business_id']
      biz_dir = data_dir / biz_id
      try:
        ans_obj = pipeline.solve_question(q, biz_dir, log_dir=log_path)
      except Exception as exc:
        ans_obj = {'id': q['id'], 'type': 'unanswerable', 'reason': f'Worker execution error: {exc}'}

      # Immediately write to output file safely
      line = json.dumps(ans_obj, ensure_ascii=False)
      with write_lock:
        with open(out_path, 'a', encoding='utf-8') as out_f:
          out_f.write(line + '\n')
          out_f.flush()

      ans_prev = f"type={ans_obj.get('type')}, answer={ans_obj.get('answer', ans_obj.get('reason'))}"
      print(f"[{idx + 1}/{len(questions)}] {q['id']} ({biz_id}) -> {ans_prev}", flush=True)
      return idx, ans_obj

    indexed = list(enumerate(questions))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
      list(executor.map(_worker, indexed))

  total_sec = time.perf_counter() - start_all
  print('=' * 60)
  print(f'COMPLETED in {total_sec:.2f} seconds ({total_sec / len(questions):.2f}s per question).')
  print(f'Submission generated at: {out_path.resolve()}')
  print('=' * 60)


if __name__ == '__main__':
  main()
