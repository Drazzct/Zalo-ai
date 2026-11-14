"""Rulebook Parser Module for Zalo AI DataMate.

Parses split-specific rulebook.md files, extracts general business rules,
temporal rules, and industry-specific regulations to guide the reasoning
engine.
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional


class RulebookParser:
  """Parses rulebook.md and extracts sectioned rules and industry-specific policies."""

  def __init__(self, rulebook_path: Path):
    if not rulebook_path.exists():
      raise FileNotFoundError(f'Rulebook file not found: {rulebook_path}')

    self.raw_text = rulebook_path.read_text(encoding='utf-8')
    self.sections = self._parse_sections()
    self.industry_rules = self._parse_industry_rules()

  def _parse_sections(self) -> Dict[str, str]:
    """Parse top-level markdown headers (## X. Title)."""
    sections = {}
    pattern = r'^##\s+(\d+\.?\s*[^#\n]+)'
    splits = re.split(pattern, self.raw_text, flags=re.MULTILINE)

    # First chunk before any ## is preamble
    if splits:
      sections['preamble'] = splits[0].strip()

    for i in range(1, len(splits), 2):
      sec_title = splits[i].strip()
      sec_body = splits[i + 1].strip() if i + 1 < len(splits) else ''
      sections[sec_title] = sec_body

    return sections

  def _parse_industry_rules(self) -> Dict[str, str]:
    """Parse industry-specific rules under section 6 (### Industry)."""
    industry_rules = {}
    # Look for Section 6: Theo ngành
    sec6_key = next((k for k in self.sections if 'Theo ngành' in k), None)
    if not sec6_key:
      return industry_rules

    sec6_text = self.sections[sec6_key]
    ind_splits = re.split(r'^###\s+([^#\n]+)', sec6_text, flags=re.MULTILINE)
    for i in range(1, len(ind_splits), 2):
      ind_name = ind_splits[i].strip()
      ind_body = ind_splits[i + 1].strip() if i + 1 < len(ind_splits) else ''
      industry_rules[ind_name] = ind_body

    return industry_rules

  def get_available_industries(self) -> List[str]:
    """Return list of industries defined in this rulebook."""
    return list(self.industry_rules.keys())

  def get_industry_rules(self, industry_name: str) -> Optional[str]:
    """Get rules for a specific industry (case-insensitive search)."""
    for name, content in self.industry_rules.items():
      if name.lower() == industry_name.lower():
        return content
    return None

  def detect_industry(self, text: str) -> Optional[str]:
    """Detect if text (e.g.

    business README or question) matches an industry.
    """
    text_lower = text.lower()
    # Prioritize specific nouns first to avoid ambiguous overlaps (e.g. 'size' in coffee vs baby diapers)
    keyword_map = {
        'Mẹ và bé': ['bỉm', 'tã', 'size bỉm', 'số sữa', 'voucher', 'thành viên mới'],
        'Sửa xe': ['lượt xe', 'biển số', 'nhớt', 'ruột', 'bảo hành', 'thợ', 'sửa điện'],
        'Cửa hàng điện thoại': ['điện thoại', 'iphone', 'samsung', 'thu máy cũ', 'trả góp'],
        'Nhà thuốc': ['thuốc', 'dược', 'hoạt chất', 'kê đơn', 'hạn dùng', 'strepsils', 'hapacol'],
        'Vật liệu xây dựng': ['xi măng', 'cát', 'đá', 'thép', 'sắt', 'đợt giao'],
        'Cà phê': ['cà phê', 'cafe', 'bạc xỉu', 'ly', 'pha chế', 'đồ uống', '(m)', '(l)'],
    }

    for ind, kws in keyword_map.items():
      if any(kw in text_lower for kw in kws):
        if ind in self.industry_rules:
          return ind

    return None

  def get_rule_summary_for_prompt(
      self, question: str, business_readme: str = ''
  ) -> str:
    """Build a concise, targeted prompt snippet of relevant rules for the question."""
    prompt_lines = [
        '### QUY TẮC KINH DOANH CHUẨN (RULEBOOK):',
        '- Doanh thu: Chỉ tính đơn không huỷ và không trả hàng (đơn có trả một phần cũng bỏ cả đơn). Bằng tổng thành tiền các dòng (đã trừ chiết khấu dòng, KHÔNG trừ voucher đơn, KHÔNG gồm VAT/ship). Loại trừ cả đơn giao không thành công (không giao được, thất bại).',
        '- Đơn bị huỷ vs Đơn trả: Đơn trả hàng KHÔNG phải đơn huỷ! Tỉ lệ huỷ đơn = (Số đơn huỷ / Tổng mọi đơn đặt trong kỳ) * 100. Tử số CHỈ tính đơn có trạng thái hủy (LOWER(trang_thai) LIKE \'%hủy%\' OR LIKE \'%huỷ%\' OR LIKE \'%cancel%\' OR LIKE \'%da huy%\'), TUYỆT ĐỐI KHÔNG cộng đơn \'trả\' hay \'hoàn\' vào tử số đơn hủy!',
        '- Bán chạy: Theo số lượng quy về đơn vị cơ bản.',
        '- Khách hàng: Shop có mã khách thì theo mã khách (khách lẻ bỏ qua). Shop không có mã thì theo tên.',
        '- Thời gian: "Hôm nay" là as_of_date. "Tháng này" = từ ngày 1 đến hết as_of_date. "Tuần này" = từ thứ Hai đến hết as_of_date.',
        '- Nợ: Đơn còn nợ > 0, gồm cả đơn trả hàng nếu còn nợ. Bỏ qua đơn COD / sàn TMĐT. Tuổi nợ = as_of_date - ngày đặt.',
    ]

    # Check for industry
    detected_ind = self.detect_industry(question + ' ' + business_readme)
    if detected_ind and detected_ind in self.industry_rules:
      prompt_lines.append(f'\n### QUY TẮC NGÀNH RIÊNG ({detected_ind}):')
      prompt_lines.append(self.industry_rules[detected_ind])

    return '\n'.join(prompt_lines)
