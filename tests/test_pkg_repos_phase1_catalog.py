"""Phase 1 package-repo catalog SoT tests."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_YML = REPO_ROOT / "docs" / "pkg-repos-catalog.yml"
CATALOG_MD = REPO_ROOT / "docs" / "pkg-repos-catalog.md"
CONTRACT = REPO_ROOT / "docs" / "pkg-repos-contract.md"
SIBLING_INFRA = REPO_ROOT.parent / "atlas-infra-edge" / "group_vars" / "all" / "atlas-infra-edge.yml"
SIBLING_INVENTORY = REPO_ROOT.parent / "atlas-inventory"

REQUIRED_NAMES = {
    "ubuntu",
    "debian-main",
    "debian-security",
    "debian-non-free",
    "pgdg-apt",
    "pgdg-yum",
    "yum_docker-ce-stable-9",
    "yum_docker-ce-stable-10",
    "debian-containerd",
    "ubuntu-containerd",
    "OL9_baseos",
    "OL9_appstream",
    "OL9_developer_EPEL",
    "OL9_codeready_builder",
    "OL10_baseos",
    "OL10_developer_EPEL",
}

REQUIRED_LEAF_KEYS = {
    "foundation_ci/postgresql",
    "foundation_ci/redis",
    "foundation_ci/kafka",
    "foundation_ci/jenkins",
    "foundation_ci/gitlab",
    "foundation_ci/infra",
    "foundation_lab/pgsql",
    "foundation_lab/kafka",
    "foundation_dev/mxhash",
    "foundation_dev/postgresql",
    "foundation_dev/redis",
    "foundation_dev/kafka",
    "foundation_dev/jenkins",
    "foundation_dev/gitlab",
    "foundation_dev/infra",
    "foundation_dev/k8s",
    "foundation_k8s_full",
    "infra_mirror_ci/infra",
    "infra_mirror_dev/mxhash",
}

# Inventory enable_repo_* that are static catalog names (not versioned k8s).
STATIC_INVENTORY_ENABLE_FLAGS = {
    "enable_repo_ubuntu",
    "enable_repo_debian_main",
    "enable_repo_debian_security",
    "enable_repo_debian_non_free",
    "enable_repo_pgdg",
    "enable_repo_yum_docker_ce_stable_9",
    "enable_repo_yum_docker_ce_stable_10",
    "enable_repo_OL9_baseos",
    "enable_repo_OL9_appstream",
    "enable_repo_OL9_addons",
    "enable_repo_OL9_developer",
    "enable_repo_OL9_developer_EPEL",
    "enable_repo_OL9_codeready_builder",
    "enable_repo_OL9_kvm",
    "enable_repo_OL9_MODRHCK",
    "enable_repo_OL9_oraclelinuxmanager210",
    "enable_repo_OL9_RDMA",
    "enable_repo_OL9_UEKR7",
    "enable_repo_OL9_UEKR8",
    "enable_repo_OL10_baseos",
    "enable_repo_OL10_appstream",
    "enable_repo_OL10_addons",
    "enable_repo_OL10_developer",
    "enable_repo_OL10_developer_EPEL",
    "enable_repo_OL10_RDMA",
    "enable_repo_OL10_UEKR8",
    "enable_repo_OL10_builder",
    "enable_repo_debian_containerd",
    "enable_repo_ubuntu_containerd",
    "enable_repo_pgdg_apt",
    "enable_repo_pgdg_yum",
}


def _load_catalog() -> dict:
    return yaml.safe_load(CATALOG_YML.read_text(encoding="utf-8"))


def _catalog_names(data: dict) -> set[str]:
    return {r["name"] for r in data["repos"]}


def _is_known_name(name: str, catalog_names: set[str], patterns: dict) -> bool:
    if name in catalog_names:
        return True
    # Versioned k8s concrete names from patterns
    if re.fullmatch(r"k8s-ubuntu-\d+\.\d+", name):
        return "k8s_apt" in patterns
    if re.fullmatch(r"k8s-\d+\.\d+", name):
        return "k8s_yum" in patterns
    return False


def _static_infra_upstreams(path: Path) -> dict[str, dict[str, str]]:
    """Parse static (non-Jinja) pkg_repo_upstreams slug → url/host."""
    text = path.read_text(encoding="utf-8")
    m = re.search(
        r"^pkg_repo_upstreams:\n(.*?)(?=\n# =+\n|\nhelm_repo_upstreams:)",
        text,
        re.S | re.M,
    )
    if not m:
        raise AssertionError("pkg_repo_upstreams block not found in infra-edge group_vars")
    block = m.group(1)
    out: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    skip_item = False
    for line in block.splitlines():
        if re.match(r"\s+- slug:", line):
            skip_item = "{{" in line
            current = None
            if skip_item:
                continue
            sm = re.match(r'\s+- slug:\s*"?([^"#]+?)"?\s*$', line)
            if not sm:
                skip_item = True
                continue
            slug = sm.group(1).strip().strip('"')
            current = {}
            out[slug] = current
            continue
        if skip_item or current is None:
            continue
        um = re.match(r'\s+upstream_url:\s*"([^"]+)"\s*$', line)
        if um:
            current["upstream_url"] = um.group(1)
            continue
        hm = re.match(r"\s+upstream_host:\s*(\S+)\s*$", line)
        if hm:
            current["upstream_host"] = hm.group(1)
    return out


def _inventory_enable_flags(root: Path) -> set[str]:
    flags: set[str] = set()
    for path in root.rglob("*.yml"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"^(enable_repo_\w+)\s*:", text, re.M):
            flags.add(m.group(1))
    return flags


class PkgReposPhase1CatalogTest(unittest.TestCase):
    def test_yaml_catalog_shape(self) -> None:
        data = _load_catalog()
        self.assertEqual(data.get("phase"), 1)
        repos = data["repos"]
        self.assertIsInstance(repos, list)
        self.assertGreaterEqual(len(repos), 29)
        names = [r["name"] for r in repos]
        self.assertEqual(len(names), len(set(names)), "duplicate catalog names")
        for name in REQUIRED_NAMES:
            self.assertIn(name, names, name)
        for repo in repos:
            self.assertIn(repo["family"], ("apt", "yum"), repo["name"])
            self.assertTrue(repo["official_url"].startswith("https://"), repo["name"])
            self.assertTrue(repo["upstream_host"], repo["name"])
            self.assertIn(repo["infra_mirror"], ("present", "missing"), repo["name"])
            self.assertTrue(repo["drop_in"].startswith("/etc/"), repo["name"])
        patterns = data.get("patterns") or {}
        self.assertIn("k8s_apt", patterns)
        self.assertIn("k8s_yum", patterns)

    def test_pgdg_marked_present_on_infra(self) -> None:
        by_name = {r["name"]: r for r in _load_catalog()["repos"]}
        self.assertEqual(by_name["pgdg-apt"]["infra_mirror"], "present")
        self.assertEqual(by_name["pgdg-yum"]["infra_mirror"], "present")

    def test_markdown_lists_every_official_url(self) -> None:
        md = CATALOG_MD.read_text(encoding="utf-8")
        self.assertIn("Phase 1 complete", md)
        self.assertIn("Phase 1 acceptance", md)
        self.assertIn("Infra mirror warm", md)
        for repo in _load_catalog()["repos"]:
            self.assertIn(repo["official_url"], md, repo["name"])
            self.assertIn(f"`{repo['name']}`", md, repo["name"])

    def test_legacy_enable_map_and_leaf_lists(self) -> None:
        data = _load_catalog()
        names = _catalog_names(data)
        patterns = data.get("patterns") or {}
        legacy = data["legacy_enable_map"]
        self.assertEqual(set(legacy["enable_repo_pgdg"]), {"pgdg-apt", "pgdg-yum"})
        self.assertEqual(legacy["enable_repo_ubuntu"], ["ubuntu"])
        self.assertEqual(legacy["enable_repo_k8s_1_36"], ["k8s-1.36"])
        self.assertEqual(legacy["enable_repo_k8s_ubuntu_1_36"], ["k8s-ubuntu-1.36"])
        for flag, targets in legacy.items():
            self.assertTrue(flag.startswith("enable_repo_"), flag)
            self.assertIsInstance(targets, list)
            self.assertTrue(targets, flag)
            for target in targets:
                self.assertTrue(
                    _is_known_name(target, names, patterns),
                    f"{flag} → {target} not in catalog/patterns",
                )
        for flag in STATIC_INVENTORY_ENABLE_FLAGS:
            self.assertIn(flag, legacy, f"missing legacy map for {flag}")

        leaves = data["example_leaf_lists"]
        for key in REQUIRED_LEAF_KEYS:
            self.assertIn(key, leaves, key)
        self.assertIn("ubuntu", leaves["foundation_ci/postgresql"])
        self.assertIn("pgdg-apt", leaves["foundation_ci/postgresql"])
        self.assertNotIn("pgdg-apt", leaves["foundation_ci/redis"])
        self.assertIn("ubuntu-containerd", leaves["infra_mirror_ci/infra"])
        self.assertIn("pgdg-apt", leaves["infra_mirror_ci/infra"])
        self.assertIn("k8s-1.36", leaves["infra_mirror_dev/mxhash"])
        self.assertIn("pgdg-yum", leaves["infra_mirror_dev/mxhash"])
        for key, items in leaves.items():
            for name in items:
                self.assertTrue(
                    _is_known_name(name, names, patterns),
                    f"{key}: unknown name {name}",
                )

    def test_contract_points_at_phase1_catalog(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("Phase 1 catalog complete", text)
        self.assertIn("pkg-repos-catalog.yml", text)

    @unittest.skipUnless(SIBLING_INFRA.is_file(), "sibling atlas-infra-edge not checked out")
    def test_infra_static_upstreams_match_catalog_when_present(self) -> None:
        catalog = {r["name"]: r for r in _load_catalog()["repos"]}
        infra = _static_infra_upstreams(SIBLING_INFRA)
        for name, repo in catalog.items():
            if repo["infra_mirror"] != "present":
                continue
            self.assertIn(name, infra, f"catalog marks {name} present but missing in infra")
            self.assertEqual(
                infra[name].get("upstream_url"),
                repo["official_url"],
                name,
            )
            self.assertEqual(
                infra[name].get("upstream_host"),
                repo["upstream_host"],
                name,
            )
        for slug, meta in infra.items():
            self.assertIn(slug, catalog, f"infra slug {slug} not in catalog")
            self.assertEqual(catalog[slug]["official_url"], meta["upstream_url"], slug)
            self.assertEqual(catalog[slug]["upstream_host"], meta["upstream_host"], slug)
        self.assertIn("pgdg-apt", infra)
        self.assertIn("pgdg-yum", infra)

    @unittest.skipUnless(SIBLING_INVENTORY.is_dir(), "sibling atlas-inventory not checked out")
    def test_inventory_enable_flags_covered_by_legacy_map(self) -> None:
        data = _load_catalog()
        legacy = data["legacy_enable_map"]
        flags = _inventory_enable_flags(SIBLING_INVENTORY)
        for flag in sorted(flags):
            if re.fullmatch(r"enable_repo_k8s_\d+_\d+", flag) or re.fullmatch(
                r"enable_repo_k8s_ubuntu_\d+_\d+", flag
            ):
                # Versioned; catalog documents 1.36 examples + patterns.
                continue
            self.assertIn(flag, legacy, f"inventory uses {flag} without legacy_enable_map entry")


if __name__ == "__main__":
    unittest.main()
