import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo_samples import create_demo_specimen, safe_csv_cell

NOW = datetime(2026, 10, 16, 11, 0, tzinfo=ZoneInfo('Asia/Seoul'))
SAMPLE = dict(code='T-DEMO-005', label='해수 A-09', type='해수', quantity=4,
              unit='병', project='가상 연안 시범조사', location='저온실 A',
              custodian='담당자 라', notes='가상 등록 테스트')

class DemoRegistrationTest(unittest.TestCase):
    def test_new_sample_includes_history_and_date(self):
        item = create_demo_specimen(SAMPLE, [], NOW)
        self.assertEqual(item['code'], 'T-DEMO-005')
        self.assertEqual(item['qty'], '4병')
        self.assertEqual(item['status'], '보관 중')
        self.assertEqual(item['created_at'], '2026-10-16 11:00')
        self.assertEqual(item['history'], [('등록', '담당자 라', '저온실 A')])

    def test_duplicate_code_case_insensitive(self):
        with self.assertRaisesRegex(ValueError, '이미 등록된'):
            create_demo_specimen(SAMPLE, [dict(code='t-demo-005')], NOW)

    def test_invalid_code_rejected(self):
        for value in ['t 001', '../bad', '=cmd', '가-01', 'a']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                create_demo_specimen({**SAMPLE, 'code': value}, [], NOW)

    def test_required_and_length_check(self):
        with self.assertRaises(ValueError):
            create_demo_specimen({**SAMPLE, 'custodian': ''}, [], NOW)
        with self.assertRaises(ValueError):
            create_demo_specimen({**SAMPLE, 'notes': 'a'*301}, [], NOW)

    def test_quantity_range_and_type(self):
        for q in [0, -1, float('nan'), float('inf'), 1000000, 'wrong']:
            with self.subTest(q=q), self.assertRaises(ValueError):
                create_demo_specimen({**SAMPLE, 'quantity': q}, [], NOW)
        with self.assertRaises(ValueError):
            create_demo_specimen({**SAMPLE, 'type': 'any'}, [], NOW)

    def test_export_formula_is_escaped(self):
        self.assertEqual(safe_csv_cell('=1+1'), "'=1+1")
        self.assertEqual(safe_csv_cell('  @LOOKUP()'), "'  @LOOKUP()")
        self.assertEqual(safe_csv_cell('정상 시료'), '정상 시료')

if __name__ == '__main__': unittest.main()
