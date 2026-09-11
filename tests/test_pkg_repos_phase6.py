"""Phase 6: publish gates — drift catalog↔infra, grep-gates, greenfield docs."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_YML = REPO_ROOT / "docs" / "pkg-repos-catalog.yml"
CATALOG_MD = REPO_ROOT / "docs" / "pkg-repos-catalog.md"
CONTRACT = REPO_ROOT / "docs" / "pkg-repos-contract.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
README = REPO_ROOT / "README.md"

SIBLING_INFRA_PRODUCT = (
    REPO_ROOT.parent / "atlas-infra-edge" / "group_vars" / "all" / "atlas-infra-edge.yml"
)
INVENTORY = REPO_ROOT.parent / "atlas-inventory"
CLUSTERCTL = REPO_ROOT.parent / "atlas-clusterctl"

PRODUCT_SIBLINGS = (
    REPO_ROOT.parent / "atlas-postgresql",
    REPO_ROOT.parent / "atlas-jenkins-agent",
    REPO_ROOT.parent / "atlas-k8s-core",
)

# On foundation overlays only (stricter).
NF_BAN_KEYS = re.compile(
    r"(?m)^(?:enable_repo_\w+|pkg_repo_name_prefix|use_internal_rpm_apt_repo|"
    r"install_managed_pkg_repos|install_k8s_pkg_repo|install_additional_repos|"
    r"pkg_repo_upstreams|pkg_repo_managed_\w+|pkg_repo_client_uri)\s*:"
)

PRODUCT_INVENTORY_NAMES = (
    "atlas-postgresql.yml",
    "atlas-jenkins-agent.yml",
    "atlas-k8s-core.yml",
    "atlas-redis.yml",
    "atlas-kafka.yml",
)


def _load_catalog() -> dict:
    return yaml.safe_load(CATALOG_YML.read_text(encoding="utf-8"))


def _static_infra_upstreams(path: Path) -> dict[str, dict[str, str]]:
    """Parse static (non-Jinja) pkg_repo_upstreams — block or flow-style list items."""
    text = path.read_text(encoding="utf-8")
    m = re.search(
        r"^pkg_repo_upstreams:\n(.*?)(?=\n# =+\n|\nhelm_repo_upstreams:|\nenable_repo_)",
        text,
        re.S | re.M,
    )
    if not m:
        raise AssertionError(f"pkg_repo_upstreams block missing in {path}")
    out: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    skip = False
    for line in m.group(1).splitlines():
        # Flow style: - { slug: name, upstream_url: "...", upstream_host: host }
        fm = re.match(
            r'\s+- \{\s*slug:\s*"?([^",{}]+?)"?\s*,\s*'
            r'upstream_url:\s*"([^"]+)"\s*,\s*'
            r"upstream_host:\s*([^,}\s]+)\s*\}\s*$",
            line,
        )
        if fm:
            slug = fm.group(1).strip()
            if "{{" in slug or "{{" in fm.group(2):
                continue
            out[slug] = {
                "upstream_url": fm.group(2),
                "upstream_host": fm.group(3),
            }
            current = None
            skip = False
            continue
        if re.match(r"\s*- slug:", line):
            skip = "{{" in line
            current = None
            if skip:
                continue
            sm = re.match(r'\s*- slug:\s*"?([^"#]+?)"?\s*$', line)
            if not sm:
                skip = True
                continue
            slug = sm.group(1).strip().strip('"')
            current = {}
            out[slug] = current
            continue
        if skip or current is None:
            continue
        um = re.match(r'\s+upstream_url:\s*"([^"]+)"\s*$', line)
        if not um:
            um = re.match(r"\s+upstream_url:\s*(\S+)\s*$", line)
        if um:
            current["upstream_url"] = um.group(1)
            continue
        hm = re.match(r"\s+upstream_host:\s*(\S+)\s*$", line)
        if hm:
            current["upstream_host"] = hm.group(1)
    return out


def _enabled_infra_names(path: Path, legacy_map: dict) -> set[str]:
    """Map enable_repo_*: true through legacy_enable_map → catalog names."""
    text = path.read_text(encoding="utf-8")
    names: set[str] = set()
    for m in re.finditer(r"^(enable_repo_\w+)\s*:\s*true\b", text, re.M):
        flag = m.group(1)
        targets = legacy_map.get(flag)
        if not targets:
            # Versioned k8s flags are in map as enable_repo_k8s_1_36 etc.
            continue
        names.update(targets)
    return names


class PkgReposPhase6PublishTest(unittest.TestCase):
    def test_contract_and_catalog_mark_phase6_done(self) -> None:
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("Acceptance (Phase 6)", contract)
        self.assertRegex(contract, r"\*\*6\*\*.*— \*\*done\*\*")
        self.assertIn("Greenfield smoke", contract)
        catalog_md = CATALOG_MD.read_text(encoding="utf-8")
        self.assertIn("**done**", catalog_md)
        self.assertRegex(
            catalog_md,
            r"\|\s*\*\*6\*\*\s*\|.*\|\s*\*\*done\*\*\s*\|",
        )

    def test_wave_d_greenfield_and_publish_surfaces(self) -> None:
        """Wave D: greenfield checklist + catalog Waves A–D + no stale empty-k8s docs."""
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("Acceptance (Wave D", contract)
        self.assertIn("cleanup_repositories: true", contract)
        self.assertIn("non-empty", contract.lower())
        self.assertIn("foundation_dev/mxhash", contract)
        self.assertIn("foundation_dev/k8s", contract)
        self.assertIn("foundation_k8s_full", contract)
        self.assertIn("tfstate-repo", contract)
        self.assertIn("Deferred / known gaps", contract)

        catalog_md = CATALOG_MD.read_text(encoding="utf-8")
        self.assertIn("Waves A–D", catalog_md)
        self.assertRegex(
            catalog_md,
            r"\|\s*\*\*A–D\*\*\s*\|.*\|\s*\*\*done\*\*\s*\|",
        )
        self.assertIn("foundation_dev/mxhash", catalog_md)
        self.assertIn("non-free-firmware", catalog_md)

        changelog = CHANGELOG.read_text(encoding="utf-8")
        self.assertIn("Wave D", changelog)
        readme = README.read_text(encoding="utf-8")
        self.assertIn("Waves A–D", readme)

        if CLUSTERCTL.is_dir():
            k8s_doc = (
                CLUSTERCTL / "docs/stacks/k8s-core.md"
            ).read_text(encoding="utf-8")
            self.assertNotIn("often `[]`", k8s_doc)
            self.assertIn("foundation_k8s_full", k8s_doc)
            # Durable TF / inventory trees — not package-repo SoT (contract boundary).
            ws = (CLUSTERCTL / "docs/workspace.md").read_text(encoding="utf-8")
            self.assertIn("tfstate", ws.lower())

    def test_changelog_and_readme_publish_surface(self) -> None:
        changelog = CHANGELOG.read_text(encoding="utf-8")
        self.assertIn("Phase 6", changelog)
        readme = README.read_text(encoding="utf-8")
        self.assertIn("Phase 0–6", readme)
        self.assertIn("test_pkg_repos_phase6.py", readme)

    @unittest.skipUnless(SIBLING_INFRA_PRODUCT.is_file(), "sibling atlas-infra-edge missing")
    def test_drift_product_infra_upstreams_match_catalog(self) -> None:
        catalog = {r["name"]: r for r in _load_catalog()["repos"]}
        infra = _static_infra_upstreams(SIBLING_INFRA_PRODUCT)
        for name, repo in catalog.items():
            if repo.get("infra_mirror") != "present":
                continue
            self.assertIn(name, infra, f"infra_mirror present but missing upstream: {name}")
            self.assertEqual(infra[name].get("upstream_url"), repo["official_url"], name)
            self.assertEqual(infra[name].get("upstream_host"), repo["upstream_host"], name)
        for slug, meta in infra.items():
            self.assertIn(slug, catalog, f"infra slug not in catalog: {slug}")
            self.assertEqual(catalog[slug]["official_url"], meta.get("upstream_url"), slug)
            self.assertEqual(catalog[slug]["upstream_host"], meta.get("upstream_host"), slug)

    @unittest.skipUnless(INVENTORY.is_dir(), "atlas-inventory missing")
    def test_drift_inventory_infra_upstreams_match_catalog(self) -> None:
        catalog = {r["name"]: r for r in _load_catalog()["repos"]}
        paths = [
            INVENTORY / "clusters/ci/infra/group_vars/all/atlas-infra-edge.yml",
            INVENTORY / "clusters/dev/mxhash/group_vars/all/atlas-infra-edge.yml",
        ]
        for path in paths:
            if not path.is_file():
                continue
            infra = _static_infra_upstreams(path)
            for name, repo in catalog.items():
                if repo.get("infra_mirror") != "present":
                    continue
                self.assertIn(name, infra, f"{path.name}: missing {name}")
                self.assertEqual(
                    infra[name].get("upstream_url"),
                    repo["official_url"],
                    f"{path}: {name}",
                )

    @unittest.skipUnless(INVENTORY.is_dir(), "atlas-inventory missing")
    def test_warm_enable_set_matches_example_leaf_lists(self) -> None:
        data = _load_catalog()
        legacy = data["legacy_enable_map"]
        mapping = {
            "infra_mirror_ci/infra": "clusters/ci/infra/group_vars/all/atlas-infra-edge.yml",
            "infra_mirror_dev/mxhash": "clusters/dev/mxhash/group_vars/all/atlas-infra-edge.yml",
        }
        for key, rel in mapping.items():
            path = INVENTORY / rel
            if not path.is_file():
                continue
            got = _enabled_infra_names(path, legacy)
            expected = set(data["example_leaf_lists"][key])
            self.assertEqual(
                got,
                expected,
                f"{key}: warm enable set drifted from example_leaf_lists",
            )

    @unittest.skipUnless(CLUSTERCTL.is_dir(), "atlas-clusterctl missing")
    def test_template_infra_warm_matches_ci_infra_example(self) -> None:
        """Wave B: _template/infra_edge warm set must include PGDG (parity with ci/infra)."""
        data = _load_catalog()
        path = (
            CLUSTERCTL
            / "clusters/_template/infra_edge/group_vars/all/atlas-infra-edge.yml"
        )
        self.assertTrue(path.is_file(), path)
        got = _enabled_infra_names(path, data["legacy_enable_map"])
        expected = set(data["example_leaf_lists"]["infra_mirror_ci/infra"])
        self.assertEqual(
            got,
            expected,
            "template infra_edge warm drifted from infra_mirror_ci/infra",
        )
        text = path.read_text(encoding="utf-8")
        self.assertIn("enable_repo_pgdg_apt: true", text)
        self.assertIn("enable_repo_pgdg_yum: true", text)
        self.assertRegex(text, r"(?m)^- slug:\s*pgdg-apt\s*$")
        self.assertRegex(text, r"(?m)^- slug:\s*pgdg-yum\s*$")

    @unittest.skipUnless(CLUSTERCTL.is_dir(), "atlas-clusterctl missing")
    def test_drift_template_infra_upstreams_match_catalog(self) -> None:
        catalog = {r["name"]: r for r in _load_catalog()["repos"]}
        path = (
            CLUSTERCTL
            / "clusters/_template/infra_edge/group_vars/all/atlas-infra-edge.yml"
        )
        if not path.is_file():
            self.skipTest("template infra_edge missing")
        infra = _static_infra_upstreams(path)
        for name, repo in catalog.items():
            if repo.get("infra_mirror") != "present":
                continue
            self.assertIn(name, infra, f"template missing upstream {name}")
            self.assertEqual(
                infra[name].get("upstream_url"),
                repo["official_url"],
                f"template {name}",
            )

    @unittest.skipUnless(INVENTORY.is_dir(), "atlas-inventory missing")
    def test_grep_gate_no_legacy_on_foundation_overlays(self) -> None:
        roots = [INVENTORY / "clusters"]
        for root in roots:
            if not root.is_dir():
                continue
            for path in root.rglob("atlas-node-foundation.yml"):
                text = path.read_text(encoding="utf-8")
                hit = NF_BAN_KEYS.search(text)
                self.assertIsNone(
                    hit,
                    f"legacy client knob in {path}: {hit.group(0) if hit else ''}",
                )

    @unittest.skipUnless(CLUSTERCTL.is_dir(), "atlas-clusterctl missing")
    def test_grep_gate_no_legacy_on_template_foundation(self) -> None:
        for path in (CLUSTERCTL / "clusters" / "_template").rglob("atlas-node-foundation.yml"):
            text = path.read_text(encoding="utf-8")
            hit = NF_BAN_KEYS.search(text)
            self.assertIsNone(hit, f"legacy client knob in {path}")

    @unittest.skipUnless(INVENTORY.is_dir(), "atlas-inventory missing")
    def test_grep_gate_product_overlays_drop_client_mode(self) -> None:
        """Non-infra product overlays must not resurrect use_internal_rpm_apt_repo / enable_repo_*."""
        root = INVENTORY / "clusters"
        if not root.is_dir():
            self.skipTest("no clusters/")
        for path in root.rglob("*.yml"):
            if path.name not in PRODUCT_INVENTORY_NAMES:
                continue
            text = path.read_text(encoding="utf-8")
            banned = (
                "use_internal_rpm_apt_repo:",
                "pkg_repo_name_prefix:",
                "enable_repo_",
                "install_managed_pkg_repos:",
            )
            for needle in banned:
                self.assertNotIn(
                    needle,
                    text,
                    f"{path}: banned client-path leftover {needle!r}",
                )

    def test_grep_gate_product_siblings_no_mode_enum(self) -> None:
        for root in PRODUCT_SIBLINGS:
            if not root.is_dir():
                continue
            catalog = root / "group_vars" / "all" / f"{root.name}.yml"
            if catalog.is_file():
                text = catalog.read_text(encoding="utf-8")
                self.assertNotIn("use_internal_rpm_apt_repo:", text, catalog)
                self.assertNotIn("pkg_repo_name_prefix:", text, catalog)
            # Role defaults / filter: mode enum must stay out of write path
            for path in root.rglob("*.yml"):
                if "group_vars" in path.parts and path.name.startswith("atlas-"):
                    text = path.read_text(encoding="utf-8")
                    self.assertNotIn(
                        "use_internal_rpm_apt_repo:",
                        text,
                        path,
                    )

    @unittest.skipUnless(INVENTORY.is_dir() and CLUSTERCTL.is_dir(), "siblings missing")
    def test_infra_template_mirror_gate_not_derived_from_client_mode(self) -> None:
        """Phase 3 formula: setup_apt_rpm_nginx follows setup_pkg_repo_nginx only."""
        paths = [
            CLUSTERCTL
            / "clusters/_template/infra_edge/group_vars/all/atlas-infra-edge.yml",
            INVENTORY / "clusters/ci/infra/group_vars/all/atlas-infra-edge.yml",
        ]
        for path in paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIn("setup_pkg_repo_nginx:", text, path)
            # Must not derive apt/rpm nginx from use_internal_rpm_apt_repo == nginx
            self.assertNotRegex(
                text,
                r"setup_apt_rpm_nginx:\s*.*use_internal_rpm_apt_repo",
                msg=f"{path}: setup_apt_rpm_nginx still derived from client mode",
            )
            self.assertRegex(
                text,
                r"setup_apt_rpm_nginx:\s*[\"']?\{\{\s*setup_pkg_repo_nginx",
                msg=f"{path}: expected setup_apt_rpm_nginx: {{{{ setup_pkg_repo_nginx }}}}",
            )

    def test_foundation_product_defaults_still_empty_pkg_repos_safe(self) -> None:
        gv = (REPO_ROOT / "group_vars" / "all" / "atlas-node-foundation.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("pkg_repos: []", gv)
        self.assertIn("pkg_repos_extra: []", gv)
        self.assertRegex(gv, r"(?m)^cleanup_repositories:\s*false\s*$")
        self.assertNotIn("enable_repo_", gv)
        self.assertNotIn("pkg_repo_name_prefix", gv)

        tasks = (
            REPO_ROOT / "roles" / "13_configure_repo" / "tasks" / "main.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("Resolve effective pkg_repos list", tasks)
        self.assertIn("_pkg_repos_effective", tasks)
        self.assertIn("Forbid cleanup_repositories with empty effective pkg_repos", tasks)

    def test_infra_overlays_drop_dead_pkg_repo_managed_knobs(self) -> None:
        """Wave C: pkg_repo_managed_* unused path knobs must not linger on infra."""
        paths: list[Path] = []
        if SIBLING_INFRA_PRODUCT.is_file():
            paths.append(SIBLING_INFRA_PRODUCT)
        if INVENTORY.is_dir():
            paths.extend(
                INVENTORY.glob("clusters/*/infra/group_vars/all/atlas-infra-edge.yml")
            )
            paths.extend(
                INVENTORY.glob("clusters/*/*/group_vars/all/atlas-infra-edge.yml")
            )
        if CLUSTERCTL.is_dir():
            paths.append(
                CLUSTERCTL
                / "clusters/_template/infra_edge/group_vars/all/atlas-infra-edge.yml"
            )
        found = False
        for path in paths:
            if not path.is_file():
                continue
            found = True
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(
                text,
                r"(?m)^pkg_repo_managed_\w+\s*:",
                f"dead pkg_repo_managed_* in {path}",
            )
        self.assertTrue(found, "expected infra-edge overlays")
