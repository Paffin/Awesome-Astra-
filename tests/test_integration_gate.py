import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("gate", Path(__file__).resolve().parents[1] / "tools/check_integration.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.report = {"snapshot_sha256": "fixture", "affected_candidates": ["core.py", "cli.py"]}
        self.ledger = {"snapshot_sha256": "fixture", "consumers": {
            p: {"disposition": "changed", "evidence": "synthetic fixture"} for p in self.report["affected_candidates"]},
            "checks": [{"kind": "entrypoint", "passed": True, "evidence": "synthetic fixture"}]}

    def test_complete(self):
        self.assertTrue(gate.check(self.report, self.ledger)["ledger_gate_passed"])

    def test_missing_consumer(self):
        del self.ledger["consumers"]["cli.py"]
        self.assertFalse(gate.check(self.report, self.ledger)["ledger_gate_passed"])

    def test_stale(self):
        self.ledger["snapshot_sha256"] = "old"
        self.assertFalse(gate.check(self.report, self.ledger)["ledger_gate_passed"])

    def test_helper_only(self):
        self.ledger["checks"][0]["kind"] = "unit"
        self.assertFalse(gate.check(self.report, self.ledger)["ledger_gate_passed"])

    def test_coverage_gap(self):
        self.report["dynamic_files"] = ["cli.py"]
        self.assertFalse(gate.check(self.report, self.ledger)["ledger_gate_passed"])

    def test_failed_check(self):
        self.ledger["checks"][0]["passed"] = False
        self.assertFalse(gate.check(self.report, self.ledger)["ledger_gate_passed"])
