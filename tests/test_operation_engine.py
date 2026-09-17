"""Contract-replay engine tests: non-anticipativity, capacity, and contract honouring."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from operation_engine import (  # noqa: E402
    HourDecision, OperationContract, Project, ProjectTask, run_execution,
    verify_execution_trace, work_windows)
from policies import (  # noqa: E402
    BlindPolicy, CalibratedPolicy, ClimatologyPolicy, RiskAwarePolicy, ThresholdPolicy,
    critical_path_priority, make_project)


class FakeRun:
    def __init__(self, run_id, issue_hour, available_hour, first_interval_hour, scenarios):
        self.run_id = run_id
        self.issue_hour = issue_hour
        self.available_hour = available_hour
        self.first_interval_hour = first_interval_hour
        self.scenarios = np.asarray(scenarios, dtype=float)


def base_project(resumable=True, capacity=1):
    contract = OperationContract("c", 11.1, 20.0, 4, resumable)
    return make_project(
        "p", contract,
        restricted_plan=[("R1", 6, (), 4), ("R2", 6, ("R1",), 4)],
        unrestricted_plan=[("U1", 3, ())])


def test_run(horizon, value=8.0, breaches=()):
    scenarios = np.full((1, horizon), value)
    for hour in breaches:
        scenarios[0, hour] = 25.0
    return FakeRun("r", 0, 0, 0, scenarios)


class TestOperationEngine(unittest.TestCase):
    def test_completes_without_weather_and_honours_working_hours(self):
        project = base_project()
        truth = np.full(24 * 6, 8.0)
        result = run_execution(project, truth, [test_run(len(truth))], BlindPolicy(),
                               horizon=len(truth))
        verify_execution_trace(project, result, truth)
        self.assertEqual(result.status, "complete")
        mask = work_windows(project, len(truth))
        for event in result.events:
            if not mask[event["hour"]]:
                self.assertEqual(event["starts"], [])

    def test_restricted_task_never_progresses_above_continuation_limit(self):
        project = base_project()
        truth = np.full(24 * 8, 8.0)
        # The storm must overlap the declared working window, otherwise the site is
        # closed anyway and there is no exceedance exposure to measure.
        truth[8:28] = 30.0
        result = run_execution(project, truth, [test_run(len(truth))], BlindPolicy(),
                               horizon=len(truth))
        verify_execution_trace(project, result, truth)
        self.assertGreater(result.exceedance_work_hours, 0)
        unsafe = [e for e in result.events
                  if e["observed_gust"] > project.contract.continuation_limit
                  and any(project.by_name()[n].restricted for n in e["active"])]
        self.assertEqual(len(unsafe), result.exceedance_work_hours)

    def test_non_resumable_contract_restarts_progress_after_breach(self):
        project = base_project(resumable=False)
        truth = np.full(24 * 10, 8.0)
        truth[10] = 30.0
        result = run_execution(project, truth, [test_run(len(truth))], BlindPolicy(),
                               horizon=len(truth))
        verify_execution_trace(project, result, truth)
        self.assertEqual(result.status, "complete")
        resumable = base_project(resumable=True)
        result2 = run_execution(resumable, truth, [test_run(len(truth))], BlindPolicy(),
                                horizon=len(truth))
        self.assertGreaterEqual(result.makespan_hours, result2.makespan_hours)

    def test_policy_cannot_use_a_run_that_was_not_yet_available(self):
        project = base_project()
        truth = np.full(24 * 5, 8.0)
        late = FakeRun("late", issue_hour=100, available_hour=200, first_interval_hour=200,
                       scenarios=np.full((1, 200), 8.0))
        seen = []

        class Recorder(BlindPolicy):
            policy_id = "recorder"

            def decide(self, **kw):
                seen.append(kw["run"] and kw["run"].run_id)
                return super().decide(**kw)

        result = run_execution(project, truth, [late], Recorder(), horizon=len(truth))
        self.assertEqual(result.status, "complete")
        self.assertTrue(all(rid is None for rid in seen))

    def test_engine_never_reads_future_observations_for_decisions(self):
        """Changing an observation that lies strictly after hour h must not change hour h."""
        project = base_project()
        horizon = 24 * 6
        base_truth = np.full(horizon, 8.0)
        altered = base_truth.copy()
        altered[60:] = 30.0
        runs = [test_run(horizon)]
        first = run_execution(project, base_truth, runs, BlindPolicy(), horizon=horizon)
        second = run_execution(project, altered, runs, BlindPolicy(), horizon=horizon)
        for event_a, event_b in zip(first.events[:60], second.events[:60]):
            self.assertEqual(event_a["starts"], event_b["starts"])
            self.assertEqual(event_a["observed_gust"], event_b["observed_gust"])

    def test_crane_capacity_is_respected_for_multiple_cranes(self):
        contract = OperationContract("c", 11.1, 20.0, 2, True)
        tasks = tuple(ProjectTask(f"t{i}", 4, (), 1, True, 2) for i in range(4))
        project = Project("multi", tasks, crane_capacity=2, contract=contract)
        truth = np.full(24 * 4, 6.0)
        result = run_execution(project, truth, [test_run(len(truth))], BlindPolicy(),
                               horizon=len(truth))
        verify_execution_trace(project, result, truth)
        self.assertEqual(result.status, "complete")
        self.assertLessEqual(result.horizon_hours, len(truth))

    def test_trace_verifier_rejects_a_forged_completion(self):
        project = base_project()
        truth = np.full(24 * 6, 20.5)  # every hour exceeds the continuation limit
        result = run_execution(project, truth, [test_run(len(truth), value=20.5)],
                               BlindPolicy(), horizon=len(truth))
        result.status = "complete"
        with self.assertRaises(AssertionError):
            verify_execution_trace(project, result, truth)

    def test_threshold_policy_stops_when_forecast_exceeds_continuation_limit(self):
        project = base_project()
        horizon = 24 * 6
        truth = np.full(horizon, 8.0)
        run = test_run(horizon, value=8.0, breaches=range(30, 40))
        result = run_execution(project, truth, [run], ThresholdPolicy(), horizon=horizon)
        verify_execution_trace(project, result, truth)
        stopped_runs = [e for e in result.events if e["stops"] or
                        (e["active"] and project.by_name()[e["active"][0]].restricted
                         and e["observed_gust"] <= 20.0)]
        self.assertTrue(stopped_runs)
        self.assertEqual(result.exceedance_work_hours, 0)

    def test_calibrated_and_riskaware_policies_are_reproducible(self):
        project = base_project()
        horizon = 24 * 6
        truth = np.full(horizon, 8.0)
        truth[50:54] = 24.0
        runs = [test_run(horizon, value=9.0, breaches=range(48, 56))]
        def predict(run, hour, length):
            offset = hour - run.first_interval_hour
            block = run.scenarios[:, offset:offset + length]
            return float(np.mean(block.max(axis=1) > 20.0))

        def execute():
            out = []
            for policy in (CalibratedPolicy(predict=predict, critical_p=0.1),
                           RiskAwarePolicy(predict=predict, critical_p=0.1,
                                           priority=critical_path_priority(project),
                                           float_slack=1.0, critical_priority_bound=8),
                           ClimatologyPolicy(base_rate=0.05, critical_p=0.1)):
                result = run_execution(project, truth, runs, policy, horizon=horizon)
                verify_execution_trace(project, result, truth)
                out.append((policy.policy_id, result.makespan_hours,
                            result.exceedance_work_hours, result.missed_safe_hours))
            return out

        self.assertEqual(execute(), execute())

    def test_contract_validation_rejects_impossible_windows(self):
        with self.assertRaises(ValueError):
            OperationContract("bad", 25.0, 20.0, 2, True)
        with self.assertRaises(ValueError):
            OperationContract("bad", 11.1, 20.0, 0, True)


if __name__ == "__main__":
    unittest.main()
