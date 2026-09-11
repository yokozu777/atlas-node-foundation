"""Phase 2 package-repo hard cut: filter + role layout tests."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROLE = REPO_ROOT / "roles" / "13_configure_repo"
FILTER = REPO_ROOT / "filter_plugins" / "pkg_repo.py"
GROUP_VARS = REPO_ROOT / "group_vars" / "all" / "atlas-node-foundation.yml"
CONTRACT = REPO_ROOT / "docs" / "pkg-repos-contract.md"


def _load_pkg_repo():
    spec = importlib.util.spec_from_file_location("pkg_repo", FILTER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class PkgReposPhase2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_pkg_repo()

    def test_resolve_static_and_patterns(self) -> None:
        ubuntu = self.mod.pkg_repo_resolve("ubuntu")
        self.assertEqual(ubuntu["family"], "apt")
        self.assertEqual(ubuntu["kind"], "ubuntu")
        self.assertFalse(self.mod.pkg_repo_applies(ubuntu, "Debian", "12"))
        self.assertTrue(self.mod.pkg_repo_applies(ubuntu, "Ubuntu", "24.04"))

        ol = self.mod.pkg_repo_resolve("OL9_baseos")
        self.assertEqual(ol["family"], "yum")
        self.assertTrue(self.mod.pkg_repo_applies(ol, "OracleLinux", "9.4"))
        self.assertFalse(self.mod.pkg_repo_applies(ol, "OracleLinux", "10.0"))

        k8s = self.mod.pkg_repo_resolve("k8s-ubuntu-1.36")
        self.assertEqual(k8s["kind"], "k8s-deb")
        self.assertEqual(k8s["needs_keyring"], "k8s")
        self.assertIsNone(self.mod.pkg_repo_resolve("not-a-real-repo"))

    def test_enrich_skips_wrong_os(self) -> None:
        repos = [
            {"name": "ubuntu", "enabled": True, "uri": "https://nexus.example/repository/ubuntu"},
            {"name": "OL9_baseos", "enabled": True, "uri": "https://nexus.example/repository/OL9_baseos"},
            {"name": "pgdg-apt", "enabled": False, "uri": "https://nexus.example/repository/pgdg-apt"},
        ]
        enriched = self.mod.pkg_repo_enrich(repos, "Ubuntu", "24.04")
        active = [r for r in enriched if r["enabled"] and r["_applies"]]
        self.assertEqual([r["name"] for r in active], ["ubuntu"])
        disabled = [r for r in enriched if (not r["enabled"]) and r["_applies"]]
        self.assertEqual([r["name"] for r in disabled], ["pgdg-apt"])

    def test_nginx_uri_slugbing(self) -> None:
        self.assertEqual(
            self.mod.pkg_repo_nginx_uri("k8s-1.36", "repo.example.com"),
            "https://k8s-1-36.repo.example.com",
        )

    def test_role_templates_are_one_per_drop_in(self) -> None:
        templates = sorted(p.name for p in (ROLE / "templates").glob("*"))
        self.assertEqual(
            templates,
            [
                "apt-acquire-by-hash.conf.j2",
                "apt-repo.sources.j2",
                "yum-repo.repo.j2",
            ],
        )
        apt = (ROLE / "templates" / "apt-repo.sources.j2").read_text(encoding="utf-8")
        self.assertIn("item.uri", apt)
        self.assertNotIn("pkg_repo_client_uri", apt)
        self.assertNotIn("enable_repo_", apt)
        self.assertNotIn("pkg_repo_name_prefix", apt)
        # Wave C: debian-non-free must not advertise Components: main
        non_free = apt.split("kind == 'debian-non-free'")[1].split("{% elif")[0]
        self.assertIn("contrib non-free non-free-firmware", non_free)
        self.assertNotIn("Components: main", non_free)
        yum = (ROLE / "templates" / "yum-repo.repo.j2").read_text(encoding="utf-8")
        self.assertIn("[{{ item.name }}]", yum)
        self.assertIn("pgsql_version", yum)

    def test_defaults_and_tasks_are_phase2(self) -> None:
        defaults = (ROLE / "defaults" / "main.yml").read_text(encoding="utf-8")
        self.assertIn("pkg_repo_base:", defaults)
        self.assertIn("pkg_repos: []", defaults)
        self.assertIn("pkg_repos_extra: []", defaults)
        self.assertNotIn("enable_repo_", defaults)
        self.assertNotIn("pkg_repo_name_prefix", defaults)
        self.assertNotIn("use_internal_rpm_apt_repo", defaults)
        self.assertNotIn("install_managed_pkg_repos", defaults)

        tasks = (ROLE / "tasks" / "main.yaml").read_text(encoding="utf-8")
        self.assertIn("Resolve effective pkg_repos list", tasks)
        self.assertIn("_pkg_repos_effective", tasks)
        self.assertIn("pkg_repos_extra", tasks)
        self.assertIn(
            '_pkg_repos_effective: "{{ (pkg_repos | default([])) + (pkg_repos_extra | default([])) }}"',
            tasks,
        )
        self.assertNotIn(
            'pkg_repos: "{{ (pkg_repos | default([])) + (pkg_repos_extra | default([])) }}"',
            tasks,
        )
        self.assertIn("pkg_repo_enrich", tasks)
        self.assertIn("apt-repo.sources.j2", tasks)
        self.assertIn("yum-repo.repo.j2", tasks)
        self.assertIn("Forbid cleanup_repositories with empty effective pkg_repos", tasks)
        self.assertIn("_pkg_repos_effective; see docs/pkg-repos-catalog.md", tasks)
        self.assertNotIn("enable_repo_", tasks)
        self.assertNotIn("pkg_repo_client_uri", tasks)
        self.assertNotIn("use_internal_rpm_apt_repo", tasks)

        filter_text = FILTER.read_text(encoding="utf-8")
        self.assertNotIn("pkg_repo_client_uri", filter_text)
        self.assertIn("pkg_repo_enrich", filter_text)
        self.assertIn("pgdg-apt", filter_text)
        self.assertIn("pgdg-yum", filter_text)

    def test_group_vars_catalog_uses_pkg_repos(self) -> None:
        catalog = GROUP_VARS.read_text(encoding="utf-8")
        self.assertIn("pkg_repo_base:", catalog)
        self.assertIn("pkg_repos: []", catalog)
        self.assertIn("pkg_repos_extra: []", catalog)
        self.assertNotIn("\nenable_repo_", catalog)
        self.assertNotIn("pkg_repo_name_prefix:", catalog)
        self.assertNotIn("install_managed_pkg_repos:", catalog)
        self.assertNotIn("nexus_base_url:", catalog)
        self.assertIn("atlas-bootstrap-OL-developer-EPEL.repo", catalog)

    def test_bootstrap_epel_has_fixed_filename(self) -> None:
        net_defaults = (
            REPO_ROOT / "roles" / "17_configure_network" / "defaults" / "main.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("atlas-bootstrap-OL-developer-EPEL.repo", net_defaults)
        self.assertNotIn("pkg_repo_name_prefix", net_defaults)
        tmpl = (
            REPO_ROOT
            / "roles"
            / "17_configure_network"
            / "templates"
            / "oracle-bootstrap-epel.repo.j2"
        ).read_text(encoding="utf-8")
        self.assertIn("[atlas-bootstrap-OL-developer-EPEL]", tmpl)

    def test_contract_marks_phase2_done(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("Phase 2", text)


if __name__ == "__main__":
    unittest.main()
