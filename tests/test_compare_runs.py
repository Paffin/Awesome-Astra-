import copy
import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("compare_runs", Path(__file__).resolve().parents[1] / "tools/compare_runs.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def fixture():
    # Synthetic parser/unit-test data. Never published as model benchmarks.
    base = dict(run_id="b", task_id="fixture", repeat=0, variant="baseline", evidence="unit-test",
                setup={k: "test" for k in module.SETUP}, input_tokens=100, cached_input_tokens=50,
                output_tokens=20, elapsed_seconds=2, accepted=True, safety_passed=True)
    candidate = copy.deepcopy(base)
    candidate.update(run_id="c", variant="candidate", input_tokens=80, elapsed_seconds=1)
    return [base, candidate]


class ComparisonTests(unittest.TestCase):
    def test_cached_input_is_not_double_counted(self):
        result = module.compare(fixture())
        self.assertEqual(result["baseline"]["total_tokens"], 120)
        self.assertEqual(result["candidate"]["total_tokens"], 100)
        self.assertTrue(result["observed_gate_passed"])

    def test_cheaper_failed_task_is_a_regression(self):
        rows = fixture()
        rows[1]["accepted"] = False
        self.assertFalse(module.compare(rows)["observed_gate_passed"])
        self.assertIsNone(module.compare(rows)["candidate"]["tokens_per_accepted_safe_task"])

    def test_safety_failure_blocks_acceptance(self):
        rows = fixture()
        rows[1]["safety_passed"] = False
        self.assertFalse(module.compare(rows)["observed_gate_passed"])

    def test_missing_partner_is_rejected(self):
        with self.assertRaises(ValueError):
            module.compare(fixture()[:1])

    def test_mismatched_model_is_rejected(self):
        rows = fixture()
        rows[1]["setup"]["model"] = "different"
        with self.assertRaises(ValueError):
            module.compare(rows)

    def test_duplicate_is_rejected(self):
        with self.assertRaises(ValueError):
            module.compare(fixture() * 2)

    def test_bad_numeric_telemetry_is_rejected(self):
        for key, value in [("input_tokens", True), ("output_tokens", -1),
                           ("cached_input_tokens", 1000), ("elapsed_seconds", float("nan")),
                           ("elapsed_seconds", float("inf")), ("elapsed_seconds", 0)]:
            with self.subTest(key=key, value=value):
                rows = fixture()
                rows[1][key] = value
                with self.assertRaises(ValueError):
                    module.compare(rows)

    def test_all_failed_is_not_a_success(self):
        rows = fixture()
        for row in rows:
            row["accepted"] = False
        self.assertFalse(module.compare(rows)["observed_gate_passed"])

    def test_empty_is_not_a_success(self):
        with self.assertRaises(ValueError):
            module.compare([])


if __name__ == "__main__":
    unittest.main()
