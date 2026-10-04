"""Layout / surface tests for atlas-node-foundation."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Every role directory must appear in playbooks/init_nodes.yaml.
EXPECTED_ROLES: tuple[str, ...] = (
    "00_ensure_workspace",
    "00_gather_facts",
    "00_init",
    "01_backup_etc",
    "02_init_sshd",
    "03_configure_users",
    "04_configure_hostname",
    "06_configure_kernel",
    "08_configure_security",
    "09_configure_locales",
    "10_manage_services",
    "07_configure_network_dns",
    "11_certificates",
    "12_date_timezone",
    "13_configure_repo",
    "14_install_software",
    "15_configure_journald",
    "16_configure_bash",
    "17_configure_network",
    "18_remove_unwanted_services",
    "19_configure_sysctl_limits",
    "20_disable_swap",
    "21_grow_disk_to_full",
    "22_extend_swap_to_root",
    "23_init_data_disk",
    "99_update_reboot",
)


def _role_tasks_main(role: str) -> Path:
    tasks = REPO_ROOT / "roles" / role / "tasks"
    for name in ("main.yaml", "main.yml"):
        candidate = tasks / name
        if candidate.is_file():
            return candidate
    return tasks / "main.yaml"


class NodeFoundationLayoutTest(unittest.TestCase):
    def test_canonical_playbook_exists(self) -> None:
        playbook = REPO_ROOT / "playbooks" / "init_nodes.yaml"
        self.assertTrue(playbook.is_file(), str(playbook))
        text = playbook.read_text(encoding="utf-8")
        self.assertIn("00_ensure_workspace", text)
        self.assertIn("00_gather_facts", text)
        self.assertNotIn("tags: [always, 00_gather_facts", text)
        self.assertIn("node_foundation_init_hosts", text)
        self.assertIn("node_foundation_network_serial", text)
        self.assertIn("17_configure_network", text)
        self.assertLess(text.find("role: 07_configure_network_dns"), text.find("role: 11_certificates"))
        dns_tasks = _role_tasks_main("07_configure_network_dns").read_text(encoding="utf-8")
        self.assertLess(
            dns_tasks.find("name: systemd-resolved.service"),
            dns_tasks.find("dest: /etc/resolv.conf"),
        )
        self.assertLess(
            dns_tasks.find("state: stopped"),
            dns_tasks.find("dest: /etc/resolv.conf"),
        )
        self.assertGreater(text.rfind("role: 17_configure_network"), text.find("role: 11_certificates"))
        self.assertNotIn("throttle:", (REPO_ROOT / "roles" / "17_configure_network" / "tasks" / "main.yaml").read_text(encoding="utf-8"))
        # Network play is last after the main role play.
        self.assertGreater(text.rfind("17_configure_network"), text.find("00_init"))
        catalog = (REPO_ROOT / "group_vars" / "all" / "atlas-node-foundation.yml").read_text(encoding="utf-8")
        self.assertIn('node_foundation_network_serial: "100%"', catalog)

    def test_all_roles_exist_and_are_wired(self) -> None:
        playbook = (REPO_ROOT / "playbooks" / "init_nodes.yaml").read_text(encoding="utf-8")
        mentioned = re.findall(r"role:\s*(\S+)", playbook)
        self.assertEqual(sorted(mentioned), sorted(EXPECTED_ROLES))

        for role in EXPECTED_ROLES:
            role_dir = REPO_ROOT / "roles" / role
            self.assertTrue(role_dir.is_dir(), role)
            self.assertTrue(_role_tasks_main(role).is_file(), f"{role}: missing tasks/main.y*ml")
            self.assertIn(f"role: {role}", playbook, role)

        # No stray role dirs left unwired.
        on_disk = sorted(p.name for p in (REPO_ROOT / "roles").iterdir() if p.is_dir())
        self.assertEqual(on_disk, sorted(EXPECTED_ROLES))

    def test_standalone_entrypoints(self) -> None:
        run_sh = REPO_ROOT / "run.sh"
        self.assertTrue(run_sh.is_file())
        self.assertTrue(run_sh.stat().st_mode & 0o111, "run.sh must be executable")
        run_text = run_sh.read_text(encoding="utf-8")
        self.assertIn("playbooks/init_nodes.yaml", run_text)
        self.assertIn("NODE_FOUNDATION_INIT_HOSTS", run_text)
        self.assertIn("inventory-example.yml", run_text)

        self.assertTrue((REPO_ROOT / "inventory-example.yml").is_file())
        self.assertTrue((REPO_ROOT / "group_vars" / "all" / "atlas-node-foundation.yml").is_file())
        self.assertTrue((REPO_ROOT / "requirements.yml").is_file())
        self.assertTrue((REPO_ROOT / "ansible.cfg").is_file())
        cfg = (REPO_ROOT / "ansible.cfg").read_text(encoding="utf-8")
        self.assertRegex(cfg, r"(?m)^\s*fact_caching\s*=\s*jsonfile\s*$")
        self.assertRegex(cfg, r"(?m)^\s*fact_caching_timeout\s*=")
        self.assertNotRegex(cfg, r"(?m)^\s*fact_caching_connection\s*=")
        self.assertIn("ANSIBLE_CACHE_PLUGIN_CONNECTION", run_text)
        self.assertIn(".ansible_facts_cache", run_text)
        self.assertIn("CLUSTER_WORKSPACE_ROOT", run_text)
        self.assertTrue((REPO_ROOT / "host_vars" / "example.yml").is_file())
        self.assertTrue((REPO_ROOT / "filter_plugins" / "pkg_repo.py").is_file())
        self.assertTrue((REPO_ROOT / "examples" / "secrets.example.yml").is_file())
        secrets = (REPO_ROOT / "examples" / "secrets.example.yml").read_text(encoding="utf-8")
        self.assertIn("CHANGEME", secrets)
        self.assertIn("EXTRA_VARS_FILE", secrets)
        self.assertNotIn("Welcomeback", secrets)
        self.assertNotIn("mxhash", secrets.lower())
        self.assertIn("EXTRA_VARS_FILE", run_text)
        self.assertIn('EXTRA_VARS+=(-e "@${EXTRA_VARS_FILE}")', run_text)

    def test_legacy_entrypoints_removed(self) -> None:
        self.assertFalse((REPO_ROOT / "init-roles.yaml").exists())
        self.assertFalse((REPO_ROOT / "group_vars" / "all" / "standalone.example.yml").exists())
        self.assertFalse((REPO_ROOT / "roles" / "13_configure_repo" / "files").exists())
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("## Removed legacy entrypoints", readme)
        self.assertIn("init-roles.yaml", readme)

    def test_inventory_example_contract(self) -> None:
        inventory = (REPO_ROOT / "inventory-example.yml").read_text(encoding="utf-8")
        self.assertIn("nodes:", inventory)
        self.assertIn("example-host:", inventory)
        self.assertIn("ansible_host:", inventory)
        self.assertIn("example.com", inventory)
        self.assertNotIn("mxhash", inventory.lower())

    def test_group_vars_catalog_contract(self) -> None:
        catalog = (REPO_ROOT / "group_vars" / "all" / "atlas-node-foundation.yml").read_text(encoding="utf-8")
        secrets = (REPO_ROOT / "group_vars" / "all" / "atlas-node-foundation.secrets.yml").read_text(
            encoding="utf-8"
        )
        for needle in (
            "cluster_domain:",
            "cluster_workspace_root:",
            "node_foundation_init_hosts:",
            "admin_user:",
            "certificates_configure:",
            "pki_ca_url:",
            "pkg_repo_base:",
            "pkg_repos: []",
            "pkg_repos_extra: []",
            "harbor_host:",
            "nexus_host:",
            "cleanup_repositories: false",
            "example.com",
        ):
            self.assertIn(needle, catalog, needle)
        for needle in (
            'initial_password: "CHANGEME"',
            'new_root_password: "CHANGEME"',
            'system_user_password: "CHANGEME"',
        ):
            self.assertNotIn(needle, catalog, needle)
            self.assertIn(needle, secrets, needle)
        self.assertNotIn("Welcomeback", catalog)
        self.assertNotIn("ca.mxhash.com", catalog)
        self.assertNotIn("ChangeMe123", catalog)

    def test_init_and_user_defaults_use_changeme(self) -> None:
        init_defaults = (REPO_ROOT / "roles" / "00_init" / "defaults" / "main.yml").read_text(
            encoding="utf-8"
        )
        user_defaults = (
            REPO_ROOT / "roles" / "03_configure_users" / "defaults" / "main.yml"
        ).read_text(encoding="utf-8")
        cert_defaults = (
            REPO_ROOT / "roles" / "11_certificates" / "defaults" / "main.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('initial_password: "CHANGEME"', init_defaults)
        self.assertIn('new_root_password: "CHANGEME"', user_defaults)
        self.assertIn('system_user_password: "CHANGEME"', user_defaults)
        self.assertIn('pki_ca_url: ""', cert_defaults)
        self.assertIn("ca_certificate_validate_certs:", cert_defaults)

    def test_readme_is_standalone_first(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for needle in (
            "# atlas-node-foundation",
            "./run.sh",
            "## Quickstart",
            "## Testing",
            "## Security",
            "group_vars/all/atlas-node-foundation.yml",
            "playbooks/init_nodes.yaml",
            "SECURITY.md",
            "CHANGEME",
        ):
            self.assertIn(needle, readme, needle)
        quick = readme.index("## Quickstart")
        integ = readme.index("## Integrations")
        self.assertLess(quick, integ)
        # Integrations may mention clusterctl; Quickstart must not require ./cluster.
        quick_block = readme[quick:integ]
        self.assertNotIn("./cluster ", quick_block)
        self.assertIn("atlas-clusterctl", readme[integ:])

    def test_date_timezone_host_chrony_gate(self) -> None:
        defaults = (
            REPO_ROOT / "roles" / "12_date_timezone" / "defaults" / "main.yml"
        ).read_text(encoding="utf-8")
        tasks = _role_tasks_main("12_date_timezone").read_text(encoding="utf-8")
        self.assertIn("ntp_manage_host_chrony: true", defaults)
        self.assertIn("ntp_manage_host_chrony", tasks)
        self.assertIn("timedatectl set-ntp false", tasks)
        self.assertIn("CanNTP", tasks)
        self.assertIn("Skip host chrony management", tasks)

    def test_bash_export_locale_gate(self) -> None:
        defaults = (
            REPO_ROOT / "roles" / "16_configure_bash" / "defaults" / "main.yml"
        ).read_text(encoding="utf-8")
        tasks = _role_tasks_main("16_configure_bash").read_text(encoding="utf-8")
        catalog = (
            REPO_ROOT / "group_vars" / "all" / "atlas-node-foundation.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("bash_export_locale: true", defaults)
        self.assertIn("bash_export_locale", tasks)
        self.assertIn("bash_export_locale: true", catalog)
        self.assertIn("export LANG=", tasks)
        self.assertIn("export LC_ALL=", tasks)


if __name__ == "__main__":
    unittest.main()
