from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "astra-repo-audit" / "scripts" / "context_budget.py"
SPEC = importlib.util.spec_from_file_location("context_budget", MODULE_PATH)
assert SPEC and SPEC.loader
context_budget = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(context_budget)


class ContextBudgetTests(unittest.TestCase):
    def test_discovers_instructions_and_excludes_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "AGENTS.md").write_text("Project rule\n", encoding="utf-8")
            skill = root / ".agents" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: demo\ndescription: Do a demo task.\n---\n\nProceed.\n",
                encoding="utf-8",
            )
            ignored = root / "node_modules" / "package" / "skills" / "bad"
            ignored.mkdir(parents=True)
            (ignored / "SKILL.md").write_text("ignored", encoding="utf-8")

            report = context_budget.build_report(root)

            self.assertEqual(report["totals"]["files"], 2)
            self.assertEqual(
                [item["kind"] for item in report["files"]],
                ["skill", "agents"],
            )
            skill_record = next(item for item in report["files"] if item["kind"] == "skill")
            self.assertEqual(skill_record["description_words"], 4)
            self.assertGreater(report["totals"]["estimated_tokens"], 0)

    def test_token_estimate_is_utf8_byte_based(self) -> None:
        self.assertEqual(context_budget.estimated_tokens("abcd"), 1)
        self.assertEqual(context_budget.estimated_tokens("abcde"), 2)
        self.assertEqual(context_budget.estimated_tokens("я"), 1)


if __name__ == "__main__":
    unittest.main()
