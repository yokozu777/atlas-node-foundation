"""Publish hygiene contracts for atlas-node-foundation (pre-public tree)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_PRODUCT_SCAN_ROOTS = (
    REPO_ROOT / "roles",
    REPO_ROOT / "playbooks",
    REPO_ROOT / "group_vars",
    REPO_ROOT / "host_vars",
    REPO_ROOT / "examples",
    REPO_ROOT / "filter_plugins",
    REPO_ROOT / "inventory-example.yml",
    REPO_ROOT / "run.sh",
    REPO_ROOT / "ansible.cfg",
    REPO_ROOT / "requirements.yml",
    REPO_ROOT / "README.md",
)
_PRODUCT_SCAN_SUFFIXES = {".yml", ".yaml", ".j2", ".sh", ".cfg", ".md", ".py"}

_FINGERPRINT_RE = re.compile(
    r"Welcomeback|"
    r"ChangeMe123|"
    r"(?<![A-Za-z0-9_-])mxhash\.com|"
    r"gitea\.mxhash|harbor\.mxhash|nexus\.mxhash|upload\.mxhash|ca\.mxhash|"
    r"/var/lib/mxhash|"
    r"BEGIN (?:OPENSSH |RSA )?PRIVATE KEY|"
    r"\bAKIA[0-9A-Z]{16}\b",
    re.IGNORECASE,
)

_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def _iter_product_files():
    for root in _PRODUCT_SCAN_ROOTS:
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            if path.suffix.lower() not in _PRODUCT_SCAN_SUFFIXES and path.name != "run.sh":
                continue
            yield path


class PublishHygieneTest(unittest.TestCase):
    def test_license_security_readme(self) -> None:
        self.assertTrue((REPO_ROOT / "LICENSE").is_file())
        self.assertTrue((REPO_ROOT / "SECURITY.md").is_file())
        self.assertTrue((REPO_ROOT / "README.md").is_file())
        self.assertTrue((REPO_ROOT / "requirements.yml").is_file())
        self.assertTrue((REPO_ROOT / "requirements-dev.txt").is_file())
        self.assertTrue((REPO_ROOT / ".ansible-lint").is_file())
        security = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("Git history note", security)
        self.assertIn("Welcomeback", security)  # documented historical fingerprint only
        self.assertIn("filter-repo", security)
        self.assertIn("docs/pre-publish.md", security)
        self.assertIn("check_pre_publish_audit.py", security)
        self.assertTrue((REPO_ROOT / "docs" / "pre-publish.md").is_file())
        self.assertTrue((REPO_ROOT / "tests" / "check_pre_publish_audit.py").is_file())
        dev = (REPO_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
        self.assertIn("ansible-lint", dev)
        self.assertIn("requirements.yml", dev)
        lint_cfg = (REPO_ROOT / ".ansible-lint").read_text(encoding="utf-8")
        self.assertIn("profile: min", lint_cfg)

    def test_readme_documents_dev_deps(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("requirements-dev.txt", readme)
        self.assertIn("ansible-lint --profile min", readme)

    def test_gitignore_excludes_runtime_secrets(self) -> None:
        text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        for needle in (
            "inventory.yml",
            "hosts",
            "secrets.yml",
            "!roles/**/tasks/secrets.yml",
            "workspace/",
            "pub_keys/",
            "*.vault",
            ".ansible_facts_cache/",
        ):
            self.assertIn(needle, text, needle)

    def test_run_sh_executable(self) -> None:
        run_sh = REPO_ROOT / "run.sh"
        self.assertTrue(run_sh.is_file())
        self.assertTrue(run_sh.stat().st_mode & 0o111, "run.sh must be executable")

    def test_no_org_fingerprint_or_secret_material_in_product_sources(self) -> None:
        hits: list[str] = []
        for path in _iter_product_files():
            text = path.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), 1):
                if _FINGERPRINT_RE.search(line):
                    hits.append(f"{path.relative_to(REPO_ROOT)}:{lineno}:{line.strip()[:120]}")
        self.assertEqual(hits, [], f"fingerprint/secret material in product sources: {hits}")

    def test_no_cyrillic_in_product_yaml_python_shell(self) -> None:
        hits: list[str] = []
        for path in _iter_product_files():
            if path.suffix.lower() not in {".yml", ".yaml", ".j2", ".py", ".sh", ".cfg"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), 1):
                if _CYRILLIC_RE.search(line):
                    hits.append(f"{path.relative_to(REPO_ROOT)}:{lineno}:{line.strip()[:100]}")
        self.assertEqual(hits, [], f"Cyrillic in product sources: {hits}")

    def test_ci_entrypoints(self) -> None:
        run_ci = REPO_ROOT / "tests" / "run_ci.sh"
        workflow = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(run_ci.is_file(), str(run_ci))
        self.assertTrue(run_ci.stat().st_mode & 0o111, "tests/run_ci.sh must be executable")
        self.assertTrue(workflow.is_file(), str(workflow))
        wf = workflow.read_text(encoding="utf-8")
        self.assertIn("./tests/run_ci.sh", wf)
        self.assertIn("requirements-dev.txt", wf)
        self.assertIn('python-version: "3.12"', wf)
        self.assertIn("ansible-galaxy collection install", wf)
        run_ci_text = run_ci.read_text(encoding="utf-8")
        self.assertIn("ansible-lint --profile min", run_ci_text)
        self.assertIn("playbooks/init_nodes.yaml", run_ci_text)
        self.assertIn("check_pre_publish_audit.py", run_ci_text)
        self.assertIn("docs/pre-publish.md", run_ci_text)

    def test_readme_documents_testing(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Testing / CI", readme)
        self.assertIn("./tests/run_ci.sh", readme)
        self.assertIn("python3 -m unittest discover", readme)
        self.assertIn("ansible-playbook --syntax-check", readme)
        self.assertIn(".github/workflows/ci.yml", readme)
        self.assertIn("docs/pre-publish.md", readme)

    def test_no_risky_tracked_secret_filenames(self) -> None:
        # Guardrail for accidental `git add` of live material (index may lag WT).
        import subprocess

        tracked = subprocess.check_output(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()
        risky = [
            rel
            for rel in tracked
            if rel.endswith("secrets.yml")
            and not rel.endswith("secrets.yml.example")
            or rel in {"inventory.yml", "hosts"}
            or "kubeconfig" in rel.lower()
            or rel.endswith((".pem", ".key"))
        ]
        self.assertEqual(risky, [], risky)


if __name__ == "__main__":
    unittest.main()
