"""Pre-publish audit surface (publish step 7)."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "tests" / "check_pre_publish_audit.py"
DOC = ROOT / "docs" / "pre-publish.md"


class PrePublishAuditTest(unittest.TestCase):
    def test_audit_script_and_doc_exist(self) -> None:
        self.assertTrue(AUDIT.is_file(), str(AUDIT))
        self.assertTrue(DOC.is_file(), str(DOC))
        text = DOC.read_text(encoding="utf-8")
        for needle in (
            "check_pre_publish_audit.py",
            "filter-repo",
            "Welcomeback",
            "./tests/run_ci.sh",
            "EXTRA_VARS_FILE",
            "examples/secrets.example.yml",
            "git ls-files inventory.yml hosts secrets.yml",
        ):
            self.assertIn(needle, text, needle)

    def test_audit_passes_on_current_tree(self) -> None:
        proc = subprocess.run(
            ["python3", str(AUDIT)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}",
        )
        self.assertIn("OK: pre-publish audit", proc.stdout)
        # HEAD still has lab fingerprints until scrub is committed + history rewritten.
        self.assertIn("WARN:", proc.stderr)

    def test_index_has_no_live_secrets(self) -> None:
        tracked = subprocess.check_output(
            ["git", "ls-files"],
            cwd=ROOT,
            text=True,
        ).splitlines()
        risky = [
            rel
            for rel in tracked
            if (
                Path(rel).name in ("secrets.yml", "secrets.yaml")
                or rel in {"inventory.yml", "hosts", "vars-file.yml"}
                or rel.startswith(("pub_keys/", "workspace/"))
            )
        ]
        self.assertEqual(risky, [], risky)

    def test_run_ci_wires_audit(self) -> None:
        run_ci = (ROOT / "tests" / "run_ci.sh").read_text(encoding="utf-8")
        self.assertIn("check_pre_publish_audit.py", run_ci)
        self.assertIn("pre-publish", run_ci.lower())


if __name__ == "__main__":
    unittest.main()
