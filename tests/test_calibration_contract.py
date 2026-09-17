"""Cross-component regression for calibration labels and operation rules."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code'))
from calibrate_gfs_knmi_pilot import fit_threshold
from core import reference_window_status


class CalibrationContractTests(unittest.TestCase):
    def test_event_labels_match_independent_one_slot_window_contract(self):
        for threshold in (11.1, 20.0):
            values = np.array([threshold - .1, threshold, threshold + .1])
            expected_breaches = sum(
                reference_window_status([value], 1, threshold, threshold)[0] == 0
                for value in values
            )
            dates = pd.to_datetime([
                f'2025-01-{day:02d}T06:00:00Z'
                for day in (1, 2, 3, 17, 18, 19, 24, 25, 26)
            ])
            frame = pd.DataFrame({
                'valid_time': dates, 'KNMI_FX_ms': np.tile(values, 3),
                'GUST_ms': np.tile([8., 12., 16.], 3),
            })
            result = fit_threshold(frame, threshold)
            for split in ('train', 'validation', 'test'):
                self.assertEqual(result['split_counts'][split]['positive_observations'], expected_breaches)
                self.assertEqual(result['scores'][split]['positive_observations'], expected_breaches)


if __name__ == '__main__':
    unittest.main()
