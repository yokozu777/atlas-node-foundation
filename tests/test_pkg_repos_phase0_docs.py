"""Phase 0 package-repo contract / catalog presence tests."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "docs" / "pkg-repos-contract.md"
CATALOG = REPO_ROOT / "docs" / "pkg-repos-catalog.md"


class PkgReposPhase0DocsTest(unittest.TestCase):
    def test_contract_locked(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("Phase 0 locked", text)
        self.assertIn("pkg_repo_base", text)
        self.assertIn("pkg_repos:", text)
        self.assertIn("pkg_repo_name_prefix", text)
        self.assertIn("upstream_host", text)
        self.assertIn("greenfield", text.lower())
        self.assertIn("pgdg-apt", text)

    def test_catalog_has_official_urls(self) -> None:
        text = CATALOG.read_text(encoding="utf-8")
        required = (
            "https://archive.ubuntu.com/ubuntu",
            "https://deb.debian.org/debian",
            "https://apt.postgresql.org/pub/repos/apt",
            "https://download.postgresql.org/pub/repos/yum",
            "https://yum.oracle.com/repo/OracleLinux/OL9/baseos/latest/x86_64/",
            "https://download.docker.com/linux/centos/9/x86_64/stable",
            "https://pkgs.k8s.io/core:/stable:/v",
            "OL9_developer_EPEL",
            "yum_docker-ce-stable-10",
            "debian-containerd",
        )
        for marker in required:
            self.assertIn(marker, text, marker)


if __name__ == "__main__":
    unittest.main()
