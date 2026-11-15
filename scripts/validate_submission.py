"""Submission format and integrity validator for Zalo AI DataMate.

Checks compliance with Section 3.2 of the Docker Submission Guideline:
- Single JSON object per line.
- Valid types: number, percent, string, date, boolean, list, table, unanswerable, abstain.
- Value types must include 'answer'.
- 'abstain' needs no 'answer'.
- 'unanswerable' may include 'reason'.
- Cross-checks with questions.jsonl (if provided) to ensure all questions are accounted for.
"""

import argparse
import json
from pathlib import Path
import sys

VALID_TYPES = {
    'number',
    'percent',
    'string',
    'date',
    'boolean',
    'list',
    'table',
    'unanswerable',
    'abstain',
}


def validate_submission(submission_path: Path, questions_path: Path = None):
  print('=' * 60)
  print(f'VALIDATING SUBMISSION: {submission_path}')
  if questions_path and questions_path.exists():
    print(f'Reference Questions  : {questions_path}')
  print('=' * 60)

  if not submission_path.exists():
    print(f'❌ ERROR: Submission file not found: {submission_path}')
    return False

  errors = []
  warnings = []
  seen_ids = set()
  type_counts = {}

  line_count = 0
  with open(submission_path, encoding='utf-8') as f:
    for line_idx, line in enumerate(f, 1):
      line_str = line.strip()
      if not line_str:
        warnings.append(f'Line {line_idx}: Empty line ignored.')
        continue

      line_count += 1
      try:
        data = json.loads(line_str)
      except json.JSONDecodeError as e:
        errors.append(f'Line {line_idx}: Invalid JSON syntax: {e}')
        continue

      if not isinstance(data, dict):
        errors.append(f'Line {line_idx}: Line is not a JSON object.')
        continue

      qid = data.get('id')
      if not qid or not isinstance(qid, str):
        errors.append(f'Line {line_idx}: Missing or non-string "id".')
        continue

      if qid in seen_ids:
        errors.append(f'Line {line_idx}: Duplicate ID "{qid}".')
      seen_ids.add(qid)

      qtype = data.get('type')
      if not qtype or qtype not in VALID_TYPES:
        errors.append(
            f'Line {line_idx} (id={qid}): Invalid type "{qtype}". Must be one of {sorted(VALID_TYPES)}'
        )
        continue

      type_counts[qtype] = type_counts.get(qtype, 0) + 1

      if qtype in {
          'number',
          'percent',
          'string',
          'date',
          'boolean',
          'list',
          'table',
      }:
        if 'answer' not in data:
          errors.append(
              f'Line {line_idx} (id={qid}): Type "{qtype}" requires an "answer" field.'
          )
        elif data['answer'] is None:
          errors.append(
              f'Line {line_idx} (id={qid}): Type "{qtype}" has null answer.'
          )
      elif qtype == 'abstain':
        # abstain needs no answer
        pass
      elif qtype == 'unanswerable':
        # unanswerable can have reason
        if 'reason' not in data and 'answer' not in data:
          warnings.append(
              f'Line {line_idx} (id={qid}): "unanswerable" type has neither "reason" nor "answer".'
          )

  # Check with reference questions if provided
  if questions_path and questions_path.exists():
    expected_ids = set()
    with open(questions_path, encoding='utf-8') as f:
      for line in f:
        if line.strip():
          item = json.loads(line)
          expected_ids.add(item['id'])

    print(f'Total questions expected : {len(expected_ids)}')
    print(f'Total lines validated    : {line_count}')
    print(f'Unique question IDs      : {len(seen_ids)}')

    missing = expected_ids - seen_ids
    if missing:
      warnings.append(
          f'{len(missing)} questions from reference are missing from submission! (Missing will count as abstain: 0 pts).'
      )
    extra = seen_ids - expected_ids
    if extra:
      errors.append(
          f'{len(extra)} question IDs in submission are NOT present in reference questions.jsonl!'
      )
  else:
    print(f'Total lines validated    : {line_count}')
    print(f'Unique question IDs      : {len(seen_ids)}')

  print('\n📊 Type Distribution:')
  for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
    pct = (count / line_count * 100) if line_count > 0 else 0
    print(f'  - {t:<15}: {count:>5} ({pct:5.1f}%)')

  if warnings:
    print(f'\n⚠️  WARNINGS ({len(warnings)}):')
    for w in warnings[:10]:
      print(f'  - {w}')
    if len(warnings) > 10:
      print(f'  ... and {len(warnings) - 10} more warnings.')

  if errors:
    print(f'\n❌ ERRORS ({len(errors)}):')
    for e in errors[:10]:
      print(f'  - {e}')
    if len(errors) > 10:
      print(f'  ... and {len(errors) - 10} more errors.')
    print('\n❌ SUBMISSION VALIDATION FAILED! Please fix errors before submitting.')
    return False
  else:
    print('\n✅ SUBMISSION VALIDATION PASSED! File conforms to official specification.')
    return True


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Validate DataMate submission.jsonl')
  parser.add_argument('submission', type=str, help='Path to submission.jsonl')
  parser.add_argument(
      '--questions',
      type=str,
      default='public_test/questions.jsonl',
      help='Path to reference questions.jsonl',
  )
  args = parser.parse_args()

  sub_path = Path(args.submission)
  q_path = Path(args.questions) if args.questions else None

  success = validate_submission(sub_path, q_path)
  sys.exit(0 if success else 1)
