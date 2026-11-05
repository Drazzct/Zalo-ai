"""Unit tests for Phase 2:

DataIngestor and SchemaProfiler.
"""

from pathlib import Path
import pytest
from src.data_ingestor import DataIngestor, parse_clean_number, parse_vietnamese_date
from src.schema_profiler import SchemaProfiler


class TestDataCleaning:

  def test_parse_clean_number(self):
    assert parse_clean_number('560,000') == 560000.0
    assert parse_clean_number('1.500.000đ') == 1500000.0
    assert parse_clean_number('4,000') == 4000.0
    assert parse_clean_number('25%') == 25.0
    assert parse_clean_number(' - ') is None
    assert parse_clean_number(12000) == 12000.0

  def test_parse_vietnamese_date(self):
    assert parse_vietnamese_date('1 thg 6 2025') == '2025-06-01'
    assert parse_vietnamese_date('15 thg 12 2025') == '2025-12-15'
    assert parse_vietnamese_date('01/03/2025') == '2025-03-01'
    assert parse_vietnamese_date('2025-04-30') == '2025-04-30'
    assert parse_vietnamese_date('14/07/2025 14:30:00') == '2025-07-14 14:30:00'


class TestIngestorAndProfiler:

  def test_ingest_biz_101_csv(self):
    # biz_101 has ban_hang.csv
    ingestor = DataIngestor(':memory:')
    tables = ingestor.ingest_business(Path('train/data/biz_101'))
    assert 'ban_hang' in tables

    # Verify query works and cleaned numbers & dates exist
    res = ingestor.con.execute(
        'SELECT ma_hoa_don, ngay_thang, thanh_tien, quy_ra_dv_le FROM ban_hang'
        ' LIMIT 5'
    ).fetchall()
    assert len(res) == 5
    # First row check
    # ngay_thang should be '2025-06-01'
    assert res[0][1] == '2025-06-01'
    # thanh_tien should be 560000.0 numeric
    assert res[0][2] == 560000.0

    # Profile biz_101
    profiler = SchemaProfiler(ingestor, Path('train/data/biz_101'))
    assert len(profiler.unit_conversions) > 0
    assert any('Coca Cola' in c for c in profiler.unit_conversions)

    min_d, max_d = profiler.get_overall_date_bounds()
    assert min_d is not None and max_d is not None

    prompt_ctx = profiler.to_prompt_context()
    assert 'ban_hang' in prompt_ctx
    assert 'QUY ĐỔI ĐƠN VỊ' in prompt_ctx
    ingestor.close()

  def test_ingest_biz_121_excel_forward_fill(self):
    # biz_121 has DonHang_ChiTiet.xlsx with header offset = 2 and grouped rows
    ingestor = DataIngestor(':memory:')
    tables = ingestor.ingest_business(Path('train/data/biz_121'))
    assert 'don_hang_chi_tiet' in tables

    # Test forward-fill: row 3, 4, 5 in DonHang_ChiTiet.xlsx had empty metadata for subsequent lines of ORD000002
    rows = ingestor.con.execute(
        'SELECT ma_don_hang, ngay_dat_hang, trang_thai_don_hang, ten_khach_hang,'
        " ten_san_pham FROM don_hang_chi_tiet WHERE ma_don_hang = 'ORD000002'"
    ).fetchall()
    # ORD000002 has multiple products (Hapacol, Hagifen, Tiffy Dey)
    assert len(rows) >= 2
    for r in rows:
      # Every product line of ORD000002 must have non-null order metadata
      assert r[0] == 'ORD000002'
      assert r[1] == '2025-03-01'
      assert r[2] == 'Đã hoàn thành'
      assert r[3] == 'Lê Phương Hoàng'

    profiler = SchemaProfiler(ingestor, Path('train/data/biz_121'))
    min_d, max_d = profiler.get_overall_date_bounds()
    assert min_d == '2025-03-01'

    ingestor.close()

  def test_ingest_biz_123_sqlite(self):
    # biz_123 has pos.sqlite
    ingestor = DataIngestor(':memory:')
    tables = ingestor.ingest_business(Path('train/data/biz_123'))
    assert len(tables) > 0

    # Query one of the tables
    sample_table = tables[0]
    res = ingestor.con.execute(f'SELECT COUNT(*) FROM "{sample_table}"').fetchone()
    assert res[0] > 0
    ingestor.close()

