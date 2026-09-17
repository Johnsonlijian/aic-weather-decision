import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from download_inputs import knmi_request_end, parse_knmi, restrict_knmi_rows


class InputTests(unittest.TestCase):
    def test_units_and_hour24(self):
        # Constructed parser fixture, NOT downloaded observations.
        r=parse_knmi('# STN,YYYYMMDD,HH,FH,FX\n260,20250101,24,50,111\n')[0]
        self.assertEqual(r['FX_ms'],11.1)
        self.assertEqual(r['interval_end'],'2025-01-02T00:00:00+00:00')
        self.assertEqual(r['interval_start'],'2025-01-01T23:00:00+00:00')
    def test_missing_preserved(self):
        r=parse_knmi('# STN,YYYYMMDD,HH,FH,FX\n260,20250101,1,50,\n')[0]
        self.assertIsNone(r['FX_ms'])
    def test_html_rejected(self):
        with self.assertRaises(ValueError):parse_knmi('<html>blocked</html>')
    def test_request_stamp_hour24_is_interval_end(self):
        self.assertEqual(knmi_request_end('2025010124').isoformat(),
                         '2025-01-02T00:00:00+00:00')
        with self.assertRaises(ValueError):
            knmi_request_end('2025010100')

    def test_restrict_rows_keeps_inclusive_interval_and_station(self):
        rows = [
            {'station_id':'260','interval_end':'2025-01-01T00:00:00+00:00'},
            {'station_id':'260','interval_end':'2025-01-01T01:00:00+00:00'},
            {'station_id':'260','interval_end':'2025-01-02T00:00:00+00:00'},
            {'station_id':'999','interval_end':'2025-01-01T01:00:00+00:00'},
        ]
        kept = restrict_knmi_rows(rows, '2025010101', '2025010124', '260:344')
        self.assertEqual([r['interval_end'] for r in kept], [
            '2025-01-01T01:00:00+00:00', '2025-01-02T00:00:00+00:00'])

    def test_restrict_rows_rejects_duplicate_station_hour(self):
        rows = [
            {'station_id':'260','interval_end':'2025-01-01T01:00:00+00:00'},
            {'station_id':'260','interval_end':'2025-01-01T01:00:00+00:00'},
        ]
        with self.assertRaises(ValueError):
            restrict_knmi_rows(rows, '2025010101', '2025010124', '260')

    def test_restrict_rows_rejects_empty_requested_interval(self):
        rows = [{'station_id':'260','interval_end':'2025-01-03T01:00:00+00:00'}]
        with self.assertRaises(ValueError):
            restrict_knmi_rows(rows, '2025010101', '2025010124', '260')
if __name__=='__main__':unittest.main()
