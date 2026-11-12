"""Benchmark Runner Script for Zalo AI DataMate.

Runs the complete ReasoningPipeline on a dataset split, outputs submission.jsonl,
generates per-question execution logs, and computes official competition metrics.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import List, Optional

# Ensure UTF-8 output and real-time line buffering on Windows
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
  sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
  sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
  sys.path.insert(0, str(ROOT_DIR))

from src.agent_pipeline import ReasoningPipeline
from src.evaluator import Evaluator
from src.llm_client import MockLLMClient, OllamaClient, OpenAICompatibleClient


def load_jsonl(path: Path) -> List[dict]:
  records = []
  with open(path, encoding='utf-8') as f:
    for line in f:
      if line.strip():
        records.append(json.loads(line))
  return records


def main():
  parser = argparse.ArgumentParser(
      description='Run DataMate benchmark on a dataset split.'
  )
  parser.add_argument(
      '--split-dir',
      type=str,
      default='train',
      help='Root directory of split (e.g. train, public_test)',
  )
  parser.add_argument(
      '--output',
      type=str,
      default='submission.jsonl',
      help='Output submission.jsonl path',
  )
  parser.add_argument(
      '--log-dir',
      type=str,
      default='result/logs',
      help='Directory for per-question logs',
  )
  parser.add_argument(
      '--limit',
      type=int,
      default=None,
      help='Limit number of questions to process (for quick testing)',
  )
  parser.add_argument(
      '--biz-id',
      type=str,
      default=None,
      help='Filter questions for a specific business_id',
  )
  parser.add_argument(
      '--evaluate',
      action='store_true',
      help='Run evaluation against answers.jsonl if available',
  )
  parser.add_argument(
      '--model-backend',
      type=str,
      choices=['ollama', 'mock', 'vllm'],
      default='ollama',
      help='LLM backend to use for code generation (default: ollama)',
  )
  parser.add_argument(
      '--model-name',
      type=str,
      default='qwen2.5-coder:3b',
      help='Model name (e.g. qwen2.5-coder:3b, qwen2.5-coder:7b)',
  )
  parser.add_argument(
      '--api-url',
      type=str,
      default='http://127.0.0.1:11434',
      help='URL of Ollama or vLLM server',
  )
  parser.add_argument(
      '--workers',
      type=int,
      default=1,
      help='Number of concurrent workers for processing questions (default: 1)',
  )
  parser.add_argument(
      '--questions-file',
      type=str,
      default=None,
      help='Path to custom questions.jsonl (e.g. rewritten/converted questions)',
  )

  args = parser.parse_args()
  split_path = Path(args.split_dir)
  q_file = Path(args.questions_file) if args.questions_file else split_path / 'questions.jsonl'
  rb_file = split_path / 'rulebook.md'
  cal_file = split_path / 'calendar.csv'
  data_dir = split_path / 'data'

  if not q_file.exists():
    raise FileNotFoundError(f'Questions file not found: {q_file}')

  questions = load_jsonl(q_file)
  if args.biz_id:
    questions = [q for q in questions if q.get('business_id') == args.biz_id]
  if args.limit:
    questions = questions[: args.limit]

  print('=' * 60)
  print(f'DATAMATE BENCHMARK RUNNER - SPLIT: {args.split_dir}')
  print(f'Total questions to process: {len(questions)}')
  print('=' * 60)

  # Initialize LLM client
  if args.model_backend == 'mock':
    llm_client = MockLLMClient()
  elif args.model_backend == 'ollama':
    llm_client = OllamaClient(model_name=args.model_name, host=args.api_url)
  elif args.model_backend == 'vllm':
    llm_client = OpenAICompatibleClient(model_name=args.model_name, base_url=args.api_url)
  else:
    llm_client = MockLLMClient()

  # Initialize pipeline
  pipeline = ReasoningPipeline(
      rulebook_path=rb_file,
      calendar_path=cal_file,
      llm_client=llm_client,
      sandbox_timeout=10.0,
      max_retries=2,
  )

  out_path = Path(args.output)
  log_path = Path(args.log_dir)
  out_path.parent.mkdir(parents=True, exist_ok=True)
  log_path.mkdir(parents=True, exist_ok=True)

  results = []
  start_all = time.perf_counter()

  if args.workers <= 1:
    with open(out_path, 'w', encoding='utf-8') as out_f:
      for i, q in enumerate(questions):
        biz_id = q['business_id']
        biz_dir = data_dir / biz_id

        ans_obj = pipeline.solve_question(q, biz_dir, log_dir=log_path)
        # Ensure clean json line
        line = json.dumps(ans_obj, ensure_ascii=False)
        out_f.write(line + '\n')
        out_f.flush()
        results.append(ans_obj)

        ans_preview = f"type={ans_obj.get('type')}, answer={ans_obj.get('answer', ans_obj.get('reason'))}"
        print(f"[{i + 1}/{len(questions)}] {q['id']} ({biz_id}) -> {ans_preview}", flush=True)
  else:
    import concurrent.futures
    print(f"Running concurrent evaluation with {args.workers} workers...")

    def _worker(item):
      idx, q = item
      b_id = q['business_id']
      b_dir = data_dir / b_id
      ans = pipeline.solve_question(q, b_dir, log_dir=log_path)
      ans_prev = f"type={ans.get('type')}, answer={ans.get('answer', ans.get('reason'))}"
      print(f"[{idx + 1}/{len(questions)}] {q['id']} ({b_id}) -> {ans_prev}", flush=True)
      return idx, ans

    indexed = list(enumerate(questions))
    ans_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
      futures = {executor.submit(_worker, it): it[0] for it in indexed}
      for fut in concurrent.futures.as_completed(futures):
        idx, ans = fut.result()
        ans_map[idx] = ans

    results = [ans_map[i] for i in range(len(questions))]
    with open(out_path, 'w', encoding='utf-8') as out_f:
      for ans in results:
        out_f.write(json.dumps(ans, ensure_ascii=False) + '\n')

  elapsed_total = time.perf_counter() - start_all
  print(
      f'\nFinished processing {len(questions)} questions in'
      f' {elapsed_total:.2f}s.'
  )
  print(f'Submission file written to: {out_path.resolve()}')
  print(f'Execution logs written to : {log_path.resolve()}')

  # Evaluation if ground truth is available
  ans_file = split_path / 'answers.jsonl'
  if args.evaluate and ans_file.exists():
    gt = load_jsonl(ans_file)
    processed_ids = {r['id'] for r in results}
    filtered_gt = [g for g in gt if g['id'] in processed_ids]
    eval_metrics = Evaluator.evaluate(results, filtered_gt)
    print('\n' + '=' * 60)
    print('BENCHMARK EVALUATION SUMMARY')
    print('=' * 60)
    print(f"Total Evaluated : {eval_metrics['total_questions']}")
    print(f"Correct (+1)    : {eval_metrics['correct']}")
    print(f"Wrong (-1)      : {eval_metrics['wrong']}")
    print(f"Abstain (0)     : {eval_metrics['abstain']}")
    print(f"TOTAL SCORE     : {eval_metrics['total_score']}")
    print(f"Accuracy        : {eval_metrics['accuracy']:.2f}%")
    print('=' * 60)


if __name__ == '__main__':
  main()

