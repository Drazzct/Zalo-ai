"""Main prediction entry point for Zalo AI DataMate.

Complies directly with the competition Docker specification:
Reads test set from --input-dir (default: /data) and writes output to --output
(default: /result/submission.jsonl)
along with per-question logs to --log-dir (default: /result/logs).
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time
from src.agent_pipeline import MockLLMClient, ReasoningPipeline


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
      default=os.environ.get('DATA_DIR', 'public_test'),
      help='Path to input split folder containing questions.jsonl, rulebook.md,'
      ' calendar.csv, data/',
  )
  parser.add_argument(
      '--output',
      type=str,
      default=os.environ.get('OUTPUT_FILE', 'submission.jsonl'),
      help='Path to output submission.jsonl',
  )
  parser.add_argument(
      '--log-dir',
      type=str,
      default=os.environ.get('LOG_DIR', 'result/logs'),
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
      default='mock',
      help='LLM backend to use for code generation',
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
  else:
    # Future extensibility for Ollama/vLLM
    llm_client = MockLLMClient()

  pipeline = ReasoningPipeline(
      rulebook_path=rb_file,
      calendar_path=cal_file,
      llm_client=llm_client,
      sandbox_timeout=10.0,
      max_retries=2,
  )

  questions = load_jsonl(q_file)
  if args.limit:
    questions = questions[: args.limit]

  print('=' * 60)
  print('ZALO AI DATAMATE - PREDICTION RUNNER')
  print(f'Input Directory  : {input_path.resolve()}')
  print(f'Total Questions  : {len(questions)}')
  print(f'Output File      : {out_path.resolve()}')
  print(f'Log Directory    : {log_path.resolve()}')
  print('=' * 60)

  start_all = time.perf_counter()
  with open(out_path, 'w', encoding='utf-8') as out_f:
    for i, q in enumerate(questions):
      biz_id = q['business_id']
      biz_dir = data_dir / biz_id

      ans_obj = pipeline.solve_question(q, biz_dir, log_dir=log_path)
      line = json.dumps(ans_obj, ensure_ascii=False)
      out_f.write(line + '\n')

      if (i + 1) % 50 == 0 or (i + 1) == len(questions):
        print(f'Processed [{i + 1}/{len(questions)}] questions...')

  total_sec = time.perf_counter() - start_all
  print('=' * 60)
  print(f'COMPLETED in {total_sec:.2f} seconds ({total_sec / len(questions):.2f}s per question).')
  print(f'Submission generated at: {out_path.resolve()}')
  print('=' * 60)


if __name__ == '__main__':
  main()
