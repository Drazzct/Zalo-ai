"""Dataset Preparation Script for Fine-tuning / Training on Zalo AI DataMate.

Prepares structured SFT (Supervised Fine-Tuning) datasets from train/questions.jsonl
and train/answers.jsonl, optimized for QLoRA / Unsloth training on Google Colab.
"""

from collections import defaultdict
import json
import os
from pathlib import Path
from typing import Dict, List, Optional


def load_jsonl(path: Path) -> List[dict]:
  records = []
  if not path.exists():
    return records
  with open(path, encoding='utf-8') as f:
    for line in f:
      if line.strip():
        records.append(json.loads(line))
  return records


def prepare_intent_and_router_dataset(
    train_dir: Path, output_file: Path
) -> int:
  """Prepare SFT dataset for Intent, Entity & Table Routing.

  Input: User question + as_of_date.
  Output: Structured JSON with metric, temporal_range, target_type, and
  keywords.
  """
  questions = load_jsonl(train_dir / 'questions.jsonl')
  answers = {a['id']: a for a in load_jsonl(train_dir / 'answers.jsonl')}

  sft_samples = []

  for q in questions:
    qid = q['id']
    biz_id = q['business_id']
    q_text = q['question']
    as_of = q['as_of_date']
    ans_meta = answers.get(qid, {})
    ans_type = ans_meta.get('type', 'number')

    # Detect domain
    q_low = q_text.lower()
    if any(
        w in q_low
        for w in [
            'nhập hàng',
            'nhap hang',
            'phiếu nhập',
            'phieu nhap',
            'mua hàng',
            'ncc',
            'nhà cung cấp',
        ]
    ):
      domain = 'nhap_hang'
      rec_table = 'danh_sach_nhap_hang'
    elif any(
        w in q_low for w in ['tồn kho', 'ton kho', 'hết hạn', 'hsd', 'còn tồn']
    ):
      domain = 'ton_kho'
      rec_table = 'bao_cao_ton_kho'
    elif any(
        w in q_low
        for w in ['thuốc', 'thuoc', 'hoạt chất', 'hoat chat', 'kê đơn', 'ke don']
    ):
      domain = 'duoc_pham'
      rec_table = 'danh_sach_thuoc'
    elif any(
        w in q_low
        for w in ['khách hàng', 'khach hang', 'sinh nhật', 'cccd', 'điểm']
    ):
      domain = 'khach_hang'
      rec_table = 'danh_sach_khach_hang'
    elif any(
        w in q_low
        for w in ['chi phí', 'chi phi', 'sổ chi', 'tiền điện', 'tiền nước']
    ):
      domain = 'chi_phi'
      rec_table = 'so_tay_chi_phi'
    else:
      domain = 'ban_hang'
      rec_table = 'danh_sach_hoa_don'

    # Build assistant target
    target_data = {
        'question_id': qid,
        'business_id': biz_id,
        'domain': domain,
        'recommended_table': rec_table,
        'expected_answer_type': ans_type,
        'requires_join': domain in ['duoc_pham', 'khach_hang'],
    }

    # Format into OpenAI / ShareGPT conversation format
    sample = {
        'messages': [
            {
                'role': 'system',
                'content': (
                    'Bạn là chuyên gia phân tích intent và điều phối dữ liệu'
                    ' cho hệ thống Zalo AI DataMate. Hãy xác định miền nghiệp'
                    ' vụ (domain), bảng đích (recommended_table), và định dạng'
                    ' đáp án (expected_answer_type) cho câu hỏi của chủ shop.'
                ),
            },
            {
                'role': 'user',
                'content': f'Câu hỏi: "{q_text}" (as_of_date: {as_of})',
            },
            {'role': 'assistant', 'content': json.dumps(target_data, ensure_ascii=False)},
        ]
    }
    sft_samples.append(sample)

  output_file.parent.mkdir(parents=True, exist_ok=True)
  with open(output_file, 'w', encoding='utf-8') as f:
    for item in sft_samples:
      f.write(json.dumps(item, ensure_ascii=False) + '\n')

  return len(sft_samples)


def main():
  root = Path('.')
  train_dir = root / 'train'
  out_path = root / 'train' / 'sft_dataset.jsonl'
  cnt = prepare_intent_and_router_dataset(train_dir, out_path)
  print(f'✅ Successfully generated {cnt} SFT training samples -> {out_path}')


if __name__ == '__main__':
  main()

