"""Baseline evaluation script for Zalo AI DataMate.

Evaluates a submission file or baseline against train/answers.jsonl.
"""

import argparse
import json
from pathlib import Path
from src.evaluator import Evaluator


def load_jsonl(path: Path):
  records = []
  with open(path, encoding='utf-8') as f:
    for line in f:
      if line.strip():
        records.append(json.loads(line))
  return records


def main():
  parser = argparse.ArgumentParser(
      description='Evaluate predictions against ground truth.'
  )
  parser.add_argument(
      '--submission',
      type=str,
      default=None,
      help='Path to submission.jsonl file',
  )
  parser.add_argument(
      '--gt',
      type=str,
      default='train/answers.jsonl',
      help='Path to ground truth answers.jsonl',
  )
  parser.add_argument(
      '--baseline',
      type=str,
      choices=['all_abstain', 'oracle'],
      default='all_abstain',
      help='Built-in baseline to evaluate if no submission provided',
  )

  args = parser.parse_args()
  gt_records = load_jsonl(Path(args.gt))
  print(f'Loaded {len(gt_records)} ground truth records from {args.gt}')

  if args.submission and Path(args.submission).exists():
    pred_records = load_jsonl(Path(args.submission))
    print(f'Loaded {len(pred_records)} predictions from {args.submission}')
  else:
    print(f"Generating built-in baseline: '{args.baseline}'...")
    if args.baseline == 'all_abstain':
      pred_records = [{'id': r['id'], 'type': 'abstain'} for r in gt_records]
    elif args.baseline == 'oracle':
      pred_records = [
          {
              'id': r['id'],
              'type': r['type'],
              'answer': r.get('answer'),
              'reason': r.get('reason'),
          }
          for r in gt_records
      ]

  results = Evaluator.evaluate(pred_records, gt_records)

  print('=' * 60)
  print('EVALUATION RESULTS')
  print('=' * 60)
  print(f"Total Questions : {results['total_questions']}")
  print(f"Correct (+1)    : {results['correct']}")
  print(f"Wrong (-1)      : {results['wrong']}")
  print(f"Abstain (0)     : {results['abstain']}")
  print(f"TOTAL SCORE     : {results['total_score']}")
  print(f"Accuracy        : {results['accuracy']:.2f}%")
  print('-' * 60)
  print('Breakdown by Answer Type:')
  for t, stats in results['type_stats'].items():
    print(
        f"  - {t:<15}: Total={stats['total']:<4} | Correct={stats['correct']:<4}"
        f" | Wrong={stats['wrong']:<4} | Abstain={stats['abstain']:<4}"
    )
  print('=' * 60)


if __name__ == '__main__':
  main()
