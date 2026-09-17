import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import numpy as np
from core import *

class WindowTests(unittest.TestCase):
    def test_contiguous(self):self.assertEqual(window_status([8]*6+[25]*2,3,11.1,20).tolist(),[1,1,1,1,0,0])
    def test_fragmented(self):self.assertEqual(int((window_status([8,8,25,8,8,25,8,8],3,11.1,20)==1).sum()),0)
    def test_start_vs_continue(self):self.assertEqual(window_status([8,15,15],3,11.1,20).tolist(),[1])
    def test_no_restart_at_continuation_limit(self):self.assertEqual(window_status([15,15,15],3,11.1,20).tolist(),[0])
    def test_threshold_equality(self):self.assertEqual(window_status([11.1,20],2,11.1,20).tolist(),[1])
    def test_single_slot(self):self.assertEqual(window_status([8,15,25],1,11.1,20).tolist(),[1,0,0])
    def test_missing_is_not_calm(self):self.assertEqual(window_status([8,np.nan],2,11.1,20).tolist(),[-1])
    def test_failure_dominates_unknown(self):self.assertEqual(window_status([25,np.nan],2,11.1,20).tolist(),[0])
    def test_short_horizon(self):self.assertEqual(len(window_status([8],2,11.1,20)),0)
    def test_bad_duration(self):
        with self.assertRaises(ValueError):window_status([8],0,11.1,20)
    def test_bad_thresholds(self):
        with self.assertRaises(ValueError):window_status([8],1,20,11.1)
    def test_scenario_missing_rejected(self):
        with self.assertRaises(ValueError):scenario_window_probability([[8,np.nan]],2,11.1,20)

class AvailabilityTests(unittest.TestCase):
    def test_future_forecast_not_selected(self):
        rows=[dict(issue_time='2025-01-01T00:00Z',available_at='2025-01-01T06:00Z',record_type='operational_archive'),
              dict(issue_time='2025-01-01T06:00Z',available_at='2025-01-01T12:00Z',record_type='operational_archive')]
        self.assertEqual(select_available_run(rows,'2025-01-01T08:00Z')['issue_time'],'2025-01-01T00:00Z')
    def test_hindcast_not_operational(self):
        with self.assertRaises(ValueError):select_available_run([dict(issue_time='2025-01-01T00:00Z',available_at='2025-01-01T06:00Z',record_type='hindcast')],'2025-01-01T08:00Z')
    def test_current_interval_max_not_available(self):
        with self.assertRaises(ValueError):assert_feature_availability(['2025-01-01T09:00Z'],'2025-01-01T08:00Z')
    def test_naive_timezone_rejected(self):
        with self.assertRaises(ValueError):parse_utc('2025-01-01T00:00')

class SchedulingTests(unittest.TestCase):
    def fixture(self):return [Task('a',2,(),(1,),(0,1,2,3,4)),Task('b',2,('a',),(1,),(0,1,2,3,4))]
    def test_optimum(self):
        r=solve_deterministic(self.fixture(),[1],6)
        self.assertEqual(r['status'],'optimal');self.assertEqual(r['makespan'],4)
    def test_precedence_detected(self):
        with self.assertRaises(ValueError):verify_schedule(self.fixture(),[1],6,{'a':2,'b':0})
    def test_resource_detected(self):
        tasks=[Task('a',2,(),(1,),(0,1,2)),Task('b',2,(),(1,),(0,1,2))]
        with self.assertRaises(ValueError):verify_schedule(tasks,[1],4,{'a':0,'b':0})
    def test_no_window(self):
        r=solve_deterministic([Task('a',2,(),(1,),())],[1],4);self.assertEqual(r['status'],'infeasible')
    def test_cycle(self):
        with self.assertRaises(ValueError):validate_problem([Task('a',1,('b',),(1,),(0,)),Task('b',1,('a',),(1,),(0,))],[1],2)

if __name__=='__main__':unittest.main()
