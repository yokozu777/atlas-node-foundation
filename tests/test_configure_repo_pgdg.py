"""PGDG coverage remains in Phase 2 pkg_repos hard cut."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROLE = REPO_ROOT / "roles" / "13_configure_repo"
FILTER = REPO_ROOT / "filter_plugins" / "pkg_repo.py"


def _load_pkg_repo():
    spec = importlib.util.spec_from_file_location("pkg_repo", FILTER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class ConfigureRepoPgdgTest(unittest.TestCase):
    def test_filter_resolves_pgdg_slugs(self) -> None:
        mod = _load_pkg_repo()
        apt = mod.pkg_repo_resolve("pgdg-apt")
        yum = mod.pkg_repo_resolve("pgdg-yum")
        self.assertEqual(apt["kind"], "pgdg-apt")
        self.assertEqual(apt["needs_keyring"], "pgdg")
        self.assertEqual(yum["kind"], "pgdg-yum")
        self.assertTrue(mod.pkg_repo_applies(yum, "OracleLinux", "9"))

    def test_templates_cover_pgdg(self) -> None:
        apt = (ROLE / "templates" / "apt-repo.sources.j2").read_text(encoding="utf-8")
        yum = (ROLE / "templates" / "yum-repo.repo.j2").read_text(encoding="utf-8")
        self.assertIn("pgdg-apt", apt)
        self.assertIn("postgresql.gpg", apt)
        self.assertIn("pgdg-yum", yum)
        self.assertIn("pgsql_version", yum)

    def test_tasks_install_pgdg_keyring(self) -> None:
        main = (ROLE / "tasks" / "main.yaml").read_text(encoding="utf-8")
        self.assertIn("pkg_repo_needs_keyring('pgdg')", main)
        self.assertIn("ACCC4CF8.asc", main)
        self.assertIn("postgresql.gpg", main)

    def test_defaults_keep_pgsql_version(self) -> None:
        defaults = (ROLE / "defaults" / "main.yml").read_text(encoding="utf-8")
        self.assertIn("pgsql_version:", defaults)
        self.assertIn('pgsql_version: "18"', defaults)


if __name__ == "__main__":
    unittest.main()
