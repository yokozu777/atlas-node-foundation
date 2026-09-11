"""Phase 5: inventory / _template foundation overlays use pkg_repos."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_YML = REPO_ROOT / "docs" / "pkg-repos-catalog.yml"
CONTRACT = REPO_ROOT / "docs" / "pkg-repos-contract.md"
INVENTORY = REPO_ROOT.parent / "atlas-inventory"
CLUSTERCTL = REPO_ROOT.parent / "atlas-clusterctl"

LEGACY_ON_NF = re.compile(
    r"(?m)^(?:enable_repo_\w+|pkg_repo_name_prefix|use_internal_rpm_apt_repo|"
    r"install_managed_pkg_repos|install_k8s_pkg_repo|install_additional_repos|"
    r"pkg_repo_upstreams|pkg_repo_managed_\w+)\s*:"
)

# Catalog example_leaf_lists key → relative path under atlas-inventory
# Effective list = env default pkg_repos + leaf pkg_repos_extra (when split).
INVENTORY_FOUNDATION_LEAVES = {
    "foundation_dev/postgresql": "clusters/dev/postgresql/group_vars/all/atlas-node-foundation.yml",
    "foundation_dev/redis": "clusters/dev/redis/group_vars/all/atlas-node-foundation.yml",
    "foundation_dev/kafka": "clusters/dev/kafka/group_vars/all/atlas-node-foundation.yml",
    "foundation_dev/jenkins": "clusters/dev/jenkins/group_vars/all/atlas-node-foundation.yml",
    "foundation_dev/gitlab": "clusters/dev/gitlab/group_vars/all/atlas-node-foundation.yml",
    "foundation_dev/infra": "clusters/dev/infra/group_vars/all/atlas-node-foundation.yml",
    "foundation_dev/k8s": "clusters/dev/k8s/group_vars/all/atlas-node-foundation.yml",
}

INVENTORY_ENV_DEFAULT_NF = (
    "clusters/dev/default/group_vars/all/atlas-node-foundation.yml"
)

TEMPLATE_FOUNDATION = {
    "postgresql": "clusters/_template/postgresql/group_vars/all/atlas-node-foundation.yml",
    "jenkins_agent": "clusters/_template/jenkins_agent/group_vars/all/atlas-node-foundation.yml",
    "redis": "clusters/_template/redis/group_vars/all/atlas-node-foundation.yml",
    "kafka": "clusters/_template/kafka/group_vars/all/atlas-node-foundation.yml",
    "infra_edge": "clusters/_template/infra_edge/group_vars/all/atlas-node-foundation.yml",
    "k8s_full": "clusters/_template/k8s_full/group_vars/all/atlas-node-foundation.yml",
}


def _enabled_names(path: Path, key: str = "pkg_repos") -> list[str]:
    """Parse a pkg_repos / pkg_repos_extra list without full YAML (Jinja-safe)."""
    text = path.read_text(encoding="utf-8")
    m = re.search(rf"(?ms)^{re.escape(key)}:\s*\n(.*?)(?=^\S|\Z)", text)
    if not m:
        if re.search(rf"(?m)^{re.escape(key)}:\s*\[\s*\]\s*$", text):
            return []
        raise AssertionError(f"{path}: {key} missing")
    block = m.group(1)
    if re.match(r"^\s*\[\s*\]\s*$", block.strip()):
        return []
    names: list[str] = []
    current: dict[str, object] | None = None
    for line in block.splitlines():
        nm = re.match(r"^\s+- name:\s*(\S+)\s*$", line)
        if nm:
            if current is not None:
                raise AssertionError(
                    f"{path}: incomplete {key} item before {nm.group(1)}"
                )
            current = {"name": nm.group(1).strip("\"'")}
            continue
        if current is None:
            continue
        em = re.match(r"^\s+enabled:\s*(\S+)\s*$", line)
        if em:
            current["enabled"] = em.group(1).lower() in ("true", "yes", "on")
            continue
        um = re.match(r'^\s+uri:\s*"([^"]+)"\s*$', line)
        if um:
            current["uri"] = um.group(1)
            for req in ("name", "enabled", "uri"):
                if req not in current:
                    raise AssertionError(
                        f"{path}: {key} item missing {req}: {current}"
                    )
            if current["enabled"]:
                uri = str(current["uri"])
                if not uri:
                    raise AssertionError(f"{path}: empty uri for {current['name']}")
                if "{{" not in uri and not uri.startswith("http"):
                    raise AssertionError(
                        f"{path}: uri must be absolute or Jinja: {uri}"
                    )
                names.append(str(current["name"]))
            current = None
            continue
    if current is not None:
        raise AssertionError(f"{path}: trailing incomplete {key} item: {current}")
    return names


def _has_list_key(path: Path, key: str) -> bool:
    text = path.read_text(encoding="utf-8")
    return bool(
        re.search(rf"(?m)^{re.escape(key)}:\s*(\[|\n)", text)
    )


def _file_enabled_repo_names(path: Path) -> list[str]:
    """Enabled names from pkg_repos and/or pkg_repos_extra on one file."""
    names: list[str] = []
    if _has_list_key(path, "pkg_repos"):
        names.extend(_enabled_names(path, "pkg_repos"))
    if _has_list_key(path, "pkg_repos_extra"):
        names.extend(_enabled_names(path, "pkg_repos_extra"))
    if not names and not _has_list_key(path, "pkg_repos") and not _has_list_key(
        path, "pkg_repos_extra"
    ):
        # Shared stubs may omit both; treat as empty.
        return []
    return names


def _effective_dev_leaf_names(
    leaf_path: Path, *, default_path: Path | None = None
) -> list[str]:
    """Cascade-equivalent effective names (shallow merge + role concat).

    If leaf declares ``pkg_repos``, that list replaces env default (shallow).
    Then append leaf ``pkg_repos_extra`` when present (role ``_pkg_repos_effective``).
    """
    if default_path is None:
        default_path = INVENTORY / INVENTORY_ENV_DEFAULT_NF
    if _has_list_key(leaf_path, "pkg_repos"):
        base = _enabled_names(leaf_path, "pkg_repos")
    elif default_path.is_file() and _has_list_key(default_path, "pkg_repos"):
        base = _enabled_names(default_path, "pkg_repos")
    else:
        base = []
    if _has_list_key(leaf_path, "pkg_repos_extra"):
        return base + _enabled_names(leaf_path, "pkg_repos_extra")
    return base


_REPO_ITEM = (
    "  - name: {name}\n"
    "    enabled: true\n"
    '    uri: "{{{{ \'{name}\' | pkg_repo_nginx_uri(pkg_repo_nginx_domain) }}}}"\n'
)


def _write_nf(path: Path, *, repos: list[str] | None = None, extra: list[str] | None = None) -> None:
    parts = ["# test nf overlay\n"]
    if repos is not None:
        parts.append("pkg_repos:\n")
        for name in repos:
            parts.append(_REPO_ITEM.format(name=name))
    if extra is not None:
        parts.append("pkg_repos_extra:\n")
        for name in extra:
            parts.append(_REPO_ITEM.format(name=name))
    path.write_text("".join(parts), encoding="utf-8")


class EffectiveDevLeafNamesTest(unittest.TestCase):
    """Unit cases: shallow leaf pkg_repos replace + extras concat."""

    def test_extras_only_prepends_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default = root / "default.yml"
            leaf = root / "leaf.yml"
            _write_nf(default, repos=["ubuntu", "debian-main"])
            _write_nf(leaf, extra=["pgdg-apt"])
            self.assertEqual(
                _effective_dev_leaf_names(leaf, default_path=default),
                ["ubuntu", "debian-main", "pgdg-apt"],
            )

    def test_empty_leaf_pkg_repos_plus_extra_drops_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default = root / "default.yml"
            leaf = root / "leaf.yml"
            _write_nf(default, repos=["ubuntu"])
            _write_nf(leaf, repos=[], extra=["pgdg-apt"])
            self.assertEqual(
                _effective_dev_leaf_names(leaf, default_path=default),
                ["pgdg-apt"],
            )

    def test_monolithic_leaf_pkg_repos_no_extra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default = root / "default.yml"
            leaf = root / "leaf.yml"
            _write_nf(default, repos=["ubuntu"])
            _write_nf(leaf, repos=["debian-main", "OL9_baseos"])
            self.assertEqual(
                _effective_dev_leaf_names(leaf, default_path=default),
                ["debian-main", "OL9_baseos"],
            )

    def test_leaf_pkg_repos_plus_extra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default = root / "default.yml"
            leaf = root / "leaf.yml"
            _write_nf(default, repos=["ubuntu"])
            _write_nf(leaf, repos=["debian-main"], extra=["pgdg-yum"])
            self.assertEqual(
                _effective_dev_leaf_names(leaf, default_path=default),
                ["debian-main", "pgdg-yum"],
            )


class PkgReposPhase5InventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = yaml.safe_load(CATALOG_YML.read_text(encoding="utf-8"))
        cls.example = cls.catalog["example_leaf_lists"]

    def test_contract_marks_phase5_done(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("Phase 5", text)
        self.assertIn("Acceptance (Phase 5)", text)
        self.assertRegex(text, r"\*\*5\*\*.*— \*\*done\*\*")

    def test_inventory_foundation_matches_example_lists(self) -> None:
        if not INVENTORY.is_dir():
            self.skipTest("atlas-inventory sibling not present")
        default_path = INVENTORY / INVENTORY_ENV_DEFAULT_NF
        if not default_path.is_file():
            self.skipTest(f"missing env default {default_path}")
        for key, rel in INVENTORY_FOUNDATION_LEAVES.items():
            path = INVENTORY / rel
            if not path.is_file():
                self.skipTest(f"missing leaf {path}")
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(LEGACY_ON_NF.search(text), f"legacy knobs in {path}")
            names = _effective_dev_leaf_names(path)
            expected = list(self.example[key])
            self.assertEqual(names, expected, key)

    def test_template_foundation_has_pkg_repos_no_legacy(self) -> None:
        if not CLUSTERCTL.is_dir():
            self.skipTest("atlas-clusterctl sibling not present")
        for name, rel in TEMPLATE_FOUNDATION.items():
            path = CLUSTERCTL / rel
            self.assertTrue(path.is_file(), path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("pkg_repos:", text, name)
            self.assertIsNone(LEGACY_ON_NF.search(text), f"legacy knobs in {path}")
            _enabled_names(path)  # schema validate

    def test_templates_align_with_catalog_guidance(self) -> None:
        if not CLUSTERCTL.is_dir():
            self.skipTest("atlas-clusterctl sibling not present")
        mapping = {
            "postgresql": "foundation_lab/pgsql",
            "jenkins_agent": "foundation_ci/jenkins",
            "redis": "foundation_ci/redis",
            "kafka": "foundation_ci/kafka",
            "infra_edge": "foundation_ci/infra",
            "k8s_full": "foundation_k8s_full",
        }
        for tmpl, catalog_key in mapping.items():
            path = CLUSTERCTL / TEMPLATE_FOUNDATION[tmpl]
            names = _enabled_names(path)
            self.assertEqual(names, list(self.example[catalog_key]), tmpl)

    def test_cleanup_true_requires_nonempty_pkg_repos(self) -> None:
        """Wave A: cleanup∧empty is forbidden on inventory + _template NF overlays."""
        paths: list[Path] = []
        if INVENTORY.is_dir():
            paths.extend(
                (INVENTORY / "clusters").rglob("atlas-node-foundation.yml")
            )
        if CLUSTERCTL.is_dir():
            # Stack leaves + shared _template/group_vars stub
            paths.extend(
                (CLUSTERCTL / "clusters").rglob("atlas-node-foundation.yml")
            )
        self.assertTrue(paths, "expected at least one foundation overlay")
        seen_shared_stub = False
        for path in paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if path.as_posix().endswith(
                "/_template/group_vars/all/atlas-node-foundation.yml"
            ):
                seen_shared_stub = True
                # Shared stub may keep empty pkg_repos only with cleanup false.
                cleanup = re.search(r"(?m)^cleanup_repositories:\s*(\S+)\s*$", text)
                self.assertIsNotNone(cleanup, path)
                self.assertNotIn(
                    cleanup.group(1).lower(),
                    ("true", "yes", "on"),
                    f"{path}: shared stub must not use cleanup∧empty",
                )
            cleanup = re.search(r"(?m)^cleanup_repositories:\s*(\S+)\s*$", text)
            if not cleanup or cleanup.group(1).lower() not in ("true", "yes", "on"):
                continue
            names = _file_enabled_repo_names(path)
            self.assertGreater(
                len(names),
                0,
                f"{path}: cleanup_repositories=true requires non-empty enabled "
                f"pkg_repos and/or pkg_repos_extra",
            )
        if CLUSTERCTL.is_dir():
            self.assertTrue(
                seen_shared_stub,
                "expected clusters/_template/group_vars/all/atlas-node-foundation.yml",
            )

    def test_nginx_foundation_uris_use_pkg_repo_nginx_uri(self) -> None:
        """Wave B: nginx leaves must bake URI via pkg_repo_nginx_uri (dot-slugbing)."""
        paths: list[Path] = []
        if INVENTORY.is_dir():
            paths.extend(
                INVENTORY.glob("clusters/*/*/group_vars/all/atlas-node-foundation.yml")
            )
        if CLUSTERCTL.is_dir():
            paths.append(
                CLUSTERCTL
                / "clusters/_template/infra_edge/group_vars/all/atlas-node-foundation.yml"
            )
        found = False
        bare_https = re.compile(r'(?m)^\s+uri:\s*"https://')
        for path in paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            uses_nginx = (
                "pkg_repo_nginx_domain:" in text or "pkg_repo_nginx_uri" in text
            )
            if not uses_nginx:
                continue
            found = True
            self.assertIn(
                "pkg_repo_nginx_uri",
                text,
                f"{path}: nginx overlay must use pkg_repo_nginx_uri filter",
            )
            self.assertIsNone(
                bare_https.search(text),
                f"{path}: bare https://…{{{{ pkg_repo_nginx_domain }}}} without pkg_repo_nginx_uri",
            )
            # Domain may live on env default while leaf only has pkg_repos_extra URIs.
            if "pkg_repo_nginx_domain:" in text:
                self.assertRegex(
                    text,
                    r'(?m)^pkg_repo_nginx_domain:\s*"(?:repo\.\{\{\s*dns_domain_suffix\s*\}\}|repo\.[a-z0-9.-]+)"\s*$',
                    f"{path}: expected pkg_repo_nginx_domain repo.{{{{ dns_domain_suffix }}}} "
                    f"or absolute repo.<domain>",
                )
        self.assertTrue(found, "expected at least one nginx foundation overlay")

    def test_postgresql_leaves_pgsql_version_only_in_product_overlay(self) -> None:
        """Wave B: no conflicting pgsql_version on foundation for postgresql leaves."""
        pairs = []
        if INVENTORY.is_dir():
            pairs.append(
                (
                    INVENTORY
                    / "clusters/dev/postgresql/group_vars/all/atlas-node-foundation.yml",
                    INVENTORY
                    / "clusters/dev/postgresql/group_vars/all/atlas-postgresql.yml",
                )
            )
        if CLUSTERCTL.is_dir():
            pairs.append(
                (
                    CLUSTERCTL
                    / "clusters/_template/postgresql/group_vars/all/atlas-node-foundation.yml",
                    CLUSTERCTL
                    / "clusters/_template/postgresql/group_vars/all/atlas-postgresql.yml",
                )
            )
        checked = 0
        for nf, product in pairs:
            if not nf.is_file() or not product.is_file():
                continue
            checked += 1
            nf_text = nf.read_text(encoding="utf-8")
            # Inventory leaves must not duplicate pgsql_version; clusterctl
            # templates may still scaffold it until a separate cleanup.
            if INVENTORY in nf.parents:
                self.assertIsNone(
                    re.search(r"(?m)^pgsql_version\s*:", nf_text),
                    f"{nf}: pgsql_version must live only in atlas-postgresql.yml",
                )
            self.assertRegex(
                product.read_text(encoding="utf-8"),
                r"(?m)^pgsql_version\s*:",
                f"{product}: missing pgsql_version SoT",
            )
        self.assertGreater(checked, 0, "expected postgresql leaf pairs")

    def test_infra_edge_yml_still_has_warm_enable_flags(self) -> None:
        """Warm cache gate remains on enable_repo_* until a dedicated infra migration."""
        if not INVENTORY.is_dir():
            self.skipTest("atlas-inventory sibling not present")
        path = INVENTORY / "clusters/dev/infra/group_vars/all/atlas-infra-edge.yml"
        if not path.is_file():
            self.skipTest("dev/infra leaf missing")
        text = path.read_text(encoding="utf-8")
        self.assertIn("enable_repo_ubuntu:", text)
        self.assertIn("enable_repo_pgdg_apt:", text)
