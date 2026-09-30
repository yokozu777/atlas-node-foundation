# atlas-node-foundation

Ansible roles for **Linux host bootstrap**: SSH/users, hardening, locales/time, certificates,
package repos, sysctl/disks, and related prep for later stack installs (Kubernetes, data-plane,
Jenkins agents, etc.).

**Canonical playbook:** `playbooks/init_nodes.yaml`  
**Runner:** `./run.sh`  
**Vars catalog:** `group_vars/all/atlas-node-foundation.yml`  
**Secrets overlay:** `group_vars/all/atlas-node-foundation.secrets.yml`  
**Package repos (Phase 0–6 + Waves A–D):** [`docs/pkg-repos-contract.md`](docs/pkg-repos-contract.md),
[`docs/pkg-repos-catalog.md`](docs/pkg-repos-catalog.md) /
[`docs/pkg-repos-catalog.yml`](docs/pkg-repos-catalog.yml) (official upstream URLs;
gates: `tests/test_pkg_repos_phase{1,2,5,6}.py`)
**License:** Apache-2.0 (see [`LICENSE`](LICENSE))

Use this repo **standalone** (`./run.sh`) or as a sibling playbook under **external orchestrator**
(`init` / `init-infra` phases). The controller does **not** vendor these roles.

```
  ./run.sh / clusterctl phase init|init-infra
              |
              v
  Play 1 localhost:  00_ensure_workspace
              |
              v
  Play 2 targets:    facts --> ssh/users --> hostname/kernel/security
              --> locales/time --> CA --> repos --> packages
              --> sysctl/swap/disks --> (optional reboot)
              |
              v
  Play 3 network:    17_configure_network (serial configurable)
```

## Compatibility

Targeted at:
- **Ubuntu** 20.04, 22.04, 24.04, 26.04
- **Debian** 11, 12, 13
- **Oracle Linux** 9, 10

BIOS and UEFI boot paths are supported. Inventory is free-form: default host pattern is `all`
(override with `node_foundation_init_hosts` / `NODE_FOUNDATION_INIT_HOSTS`).

Example layout (see `inventory-example.yml`):

```yaml
all:
  children:
    nodes:
      hosts:
        example-host:
          ansible_host: 192.168.1.100
          hostname: example-host.example.com
```

## Quickstart

### Prerequisites

- Ansible **2.14+** recommended (distro package or venv — not pinned in `requirements-dev.txt`)
- Galaxy collections: `ansible-galaxy collection install -r requirements.yml` (`ansible.posix`)
- Optional CI tools: `python3 -m pip install -r requirements-dev.txt` (`ansible-lint`)
- SSH access to targets (Python 3 on targets)
- Replace every `CHANGEME` in `group_vars/all/atlas-node-foundation.yml` when using password auth (prefer SSH keys + Vault)

### Clone

```bash
git clone <atlas-node-foundation-url>
cd atlas-node-foundation
ansible-galaxy collection install -r requirements.yml
```

### Inventory

```bash
cp inventory-example.yml inventory.yml   # gitignored
vi inventory.yml
```

Set `ansible_host` (and optional per-host `hostname:`) on every target.

### Variables

**SoT:** `group_vars/all/atlas-node-foundation.yml` — documented defaults per role. Deep knobs also live in
`roles/*/defaults/main.yml`.

Minimum connection / identity knobs:

```yaml
admin_user: localuser
ansible_user: "{{ admin_user }}"
initial_user: "{{ admin_user }}"
system_user: "{{ admin_user }}"
init_ssh_connect: key                 # or: password
initial_password: "CHANGEME"          # only if password auth; prefer keys + vault
cluster_domain: k8s.example.com       # workspace id SoT for 00_ensure_workspace
```

SSH keys (recommended):

```bash
export SSH_KEY="$HOME/.ssh/id_ed25519"
# optional: drop .pub files into pub_keys/ (gitignored) and set pub_keys_folder: pub_keys/
```

Optional host overlays:

```bash
cp host_vars/example.yml host_vars/<inventory_hostname>.yml
```

### Run

```bash
./run.sh                              # full init
./run.sh --tags 00_init,02_init_sshd,03_configure_users
./run.sh --skip-tags 99_update_reboot
./run.sh --check -v                   # dry-run
```

Or manually:

```bash
ansible-playbook -i inventory.yml playbooks/init_nodes.yaml \
  -e node_foundation_init_hosts=all
```

Named inventory group:

```bash
NODE_FOUNDATION_INIT_HOSTS=nodes ./run.sh
```

### `./run.sh` environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `INVENTORY` | `inventory.yml` or `inventory-example.yml` | Inventory path |
| `PLAYBOOK` | `playbooks/init_nodes.yaml` | Playbook path |
| `NODE_FOUNDATION_INIT_HOSTS` | `all` | Ansible host pattern |
| `EXTRA_VARS_FILE` | empty | Optional `ansible -e @file` (vaulted secrets; see `examples/`) |
| `SSH_KEY` / `ANSIBLE_PRIVATE_KEY_FILE` | `~/.ssh/id_ed25519` or `id_rsa` | SSH private key |
| `CLUSTER_WORKSPACE_ID` | `k8s.example.com` | Workspace directory name |
| `CLUSTER_WORKSPACE_PARENT` | `./workspace` | Parent dir for workspaces |
| `CLUSTER_WORKSPACE_ROOT` | `<parent>/<id>` | Full workspace path |
| `ANSIBLE_CACHE_PLUGIN_CONNECTION` | `<workspace>/.ansible_facts_cache` | Fact cache (tag-split runs) |
| `ANSIBLE_CONFIG` | `./ansible.cfg` | Ansible config (`fact_caching=jsonfile`) |

All extra CLI arguments are forwarded to `ansible-playbook`.

## Role catalog

### Controller / facts
- **00_ensure_workspace** — controller workspace (`cluster_workspace_root`, logs, ansible temps)
- **00_gather_facts** — explicit `00_gather_facts` tag (clusterctl first remote init step; not `always`); persists via jsonfile fact cache for later `--tags`

### System initialization
- **00_init** — initial connection helpers / OS detection
- **01_backup_etc** — backup `/etc` before changes
- **99_update_reboot** — updates, optional cron scheduler, optional reboot (final)

### SSH / users
- **02_init_sshd** — SSH port, root login, password auth policy
- **03_configure_users** — system user, root password (opt-in), `pub_keys/`

### System / performance
- **04_configure_hostname** — hostname from inventory / host_vars
- **06_configure_kernel** — GRUB/EFI, P-State, SMT, IPv6, IOMMU
- **18_remove_unwanted_services** — cloud-init, snap, resolved, unattended-upgrades, …
- **19_configure_sysctl_limits** — limits + sysctl (bridge/conntrack friendly)
- **20_disable_swap** / **21_grow_disk_to_full** / **22_extend_swap_to_root** / **23_init_data_disk**

### Security / locale / time / certs
- **08_configure_security** — SELinux/AppArmor knobs
- **09_configure_locales** / **12_date_timezone** — locales, timezone, NTP
  (host chrony; set `ntp_manage_host_chrony: false` when another stack owns
  the clock, e.g. infra-edge NTP compose)
- **10_manage_services** — enable/disable units
- **07_configure_network_dns** — write `dns_servers` to `/etc/resolv.conf` before CA download
- **11_certificates** — CA URL download and/or custom cert dir

### Repos / packages / services / shell
- **13_configure_repo** — managed APT/YUM drop-ins from `pkg_repos` (+ optional `pkg_repos_extra`)
  ([`docs/pkg-repos-contract.md`](docs/pkg-repos-contract.md))
- **14_install_software** — install/remove packages
- **10_manage_services** — enable/disable units
- **15_configure_journald** / **16_configure_bash**

### Network
- **17_configure_network** — systemd-networkd
  - Batching via `node_foundation_network_serial` (default `"100%"` = full parallel)
  - Set to `1` for one-host-at-a-time handoff when SSH flap risk is high

## Role execution order

`playbooks/init_nodes.yaml`:

```
  localhost:     00_ensure_workspace
       |
       v
  targets:       00_gather_facts --> 00_init --> backup --> sshd --> users
       --> hostname --> kernel --> security --> locales --> services
       --> dns --> certificates --> timezone --> repos --> packages
       --> journald --> bash --> remove_unwanted --> sysctl
       --> disable_swap --> grow_disk --> extend_swap --> data_disk
       --> update_reboot
       |
       v
  targets (network play):  17_configure_network
```

**Play 1 — localhost**
1. **00_ensure_workspace** (tag `00_ensure_workspace`)

**Play 2 — targets** (`node_foundation_init_hosts`)
2. **00_gather_facts** (tag `00_gather_facts`) → **00_init** → **01_backup_etc** → **02_init_sshd** →
   **03_configure_users** → **04_configure_hostname** → **06_configure_kernel** →
   **08_configure_security** → **09_configure_locales** → **10_manage_services** →
   **10_manage_services** → **07_configure_network_dns** → **11_certificates** → **12_date_timezone** → **13_configure_repo** → **14_install_software** →
   **15_configure_journald** → **16_configure_bash** → **18_remove_unwanted_services** →
   **19_configure_sysctl_limits** → **20_disable_swap** → **21_grow_disk_to_full** →
   **22_extend_swap_to_root** → **23_init_data_disk** → **99_update_reboot**

**Play 3 — targets (network; `node_foundation_network_serial`, default `"100%"`)**
3. **17_configure_network**

## Variables

All knobs are documented inline in `group_vars/all/atlas-node-foundation.yml` (purpose, defaults, examples, warnings).
Workspace / targeting contract:

- `cluster_domain`, `k8s_cluster_domain`, `cluster_workspace_parent`, `cluster_workspace_id`,
  `cluster_workspace_root`
- `node_foundation_init_hosts`
- `admin_user` (drives `ansible_user` / `initial_user` / `system_user`)

### Configuration examples

```yaml
# group_vars/all/atlas-node-foundation.yml — baseline
admin_user: localuser
init_ssh_connect: key
timezone: Europe/Moscow
ntp_servers:
  - 192.168.1.1
# ntp_manage_host_chrony: false   # infra NTP server leaf (compose owns clock)
# configure_locales: false
# bash_export_locale: false       # pair with locales off — no LANG/LC_ALL in profile
```

```yaml
# group_vars/all/atlas-node-foundation.yml — hardening / repos sketch
disable_root_login: true
disable_password_auth: true
change_default_ssh_port: true
new_ssh_port: 2222
certificates_configure: true
pki_ca_url:
  - "https://ca.example.com:8443/roots.pem"
pkg_repo_base: https://nexus.example.com/repository
# cleanup_repositories: true requires non-empty combined list (role asserts)
cleanup_repositories: true
pkg_repos:
  - name: ubuntu
    enabled: true
    uri: "{{ pkg_repo_base }}/ubuntu"
# Optional stack extras (concat in 13_configure_repo):
# pkg_repos_extra:
#   - name: pgdg-apt
#     enabled: true
#     uri: "{{ pkg_repo_base }}/pgdg-apt"
# See docs/pkg-repos-contract.md
update_now: false
reboot_system: false
```

```yaml
# host_vars/<inventory_hostname>.yml
hostname: web-server.example.com
```

## Advanced usage

```bash
# Encrypt a password string for group_vars
ansible-vault encrypt_string 'MySecurePassword' --name 'initial_password'

# Optional secrets overlay (keep outside the repo)
cp examples/secrets.example.yml ~/node-foundation-secrets.yml
# edit; optionally: ansible-vault encrypt ~/node-foundation-secrets.yml
EXTRA_VARS_FILE=~/node-foundation-secrets.yml ./run.sh

export SSH_KEY="/path/to/your/key"
./run.sh

ansible-playbook -i inventory.yml playbooks/init_nodes.yaml \
  -e node_foundation_init_hosts=all \
  --private-key "/path/to/your/key"
```

## Troubleshooting

**Connection**
- Export `SSH_KEY` / `ANSIBLE_PRIVATE_KEY_FILE` and `chmod 600` the key
- Match `admin_user` / `ansible_user` to an account with SSH (+ sudo)
- Ensure the public key is on the target (or via `pub_keys/`)

**Empty play / wrong hosts**
- Default pattern is `all`; use `NODE_FOUNDATION_INIT_HOSTS=nodes ./run.sh` for a group

**Workspace asserts (`00_ensure_workspace`)**
- Defaults for `cluster_domain` / `cluster_workspace_*` are in `group_vars/all/atlas-node-foundation.yml`
- Override: `CLUSTER_WORKSPACE_ID=my-lab ./run.sh`

**Role-specific**
- Check `roles/<role>/defaults/main.yml` and override in `group_vars` / `host_vars`

**Collections**

```bash
ansible-galaxy collection install -r requirements.yml
```

## Testing / CI

Contributor deps (optional):

```bash
python3 -m pip install -r requirements-dev.txt
ansible-galaxy collection install -r requirements.yml
```

Local checks (same gates as GitHub Actions):

```bash
./tests/run_ci.sh
# or piecemeal:
python3 -m unittest discover -s tests -v
ansible-playbook --syntax-check -i inventory-example.yml playbooks/init_nodes.yaml
ansible-lint --profile min
```

Layout / hygiene coverage: `tests/test_layout_surface.py`, `tests/test_publish_hygiene.py`,
`tests/test_configure_repo_pgdg.py`, `tests/test_pkg_repos_phase2.py`,
`tests/test_pkg_repos_phase5.py`, `tests/test_pkg_repos_phase6.py`,
`tests/test_pre_publish_audit.py`.

CI workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (unittest, syntax-check,
ansible-lint `min`, publish hygiene, pre-publish audit).

Before a public remote, follow [`docs/pre-publish.md`](docs/pre-publish.md).

Optional stricter lint locally: `ansible-lint --profile basic` (may surface legacy style
findings; not a merge gate yet).

## Project structure

```
atlas-node-foundation/
├── playbooks/
│   └── init_nodes.yaml
├── run.sh
├── ansible.cfg
├── requirements.yml            # Galaxy collections (runtime)
├── requirements-dev.txt        # ansible-lint (CI / contributors)
├── .ansible-lint
├── inventory-example.yml
├── group_vars/
│   └── all/
│       └── atlas-node-foundation.yml                 # documented catalog (CHANGEME for secrets)
├── examples/
│   ├── README.md
│   └── secrets.example.yml     # EXTRA_VARS_FILE template (do not commit filled copy)
├── host_vars/
│   └── example.yml
├── roles/
│   ├── 00_ensure_workspace/
│   ├── 00_gather_facts/
│   ├── 00_init/
│   ├── …
│   └── 99_update_reboot/
├── filter_plugins/
├── tests/
│   ├── run_ci.sh
│   ├── check_pre_publish_audit.py
│   └── test_*.py
├── docs/
│   └── pre-publish.md          # maintainer checklist before public remote
├── .github/workflows/
│   └── ci.yml
├── LICENSE
├── SECURITY.md
└── pub_keys/                   # gitignored — create locally
```

## Removed legacy entrypoints

Do **not** look for these — they were removed from the public tree:

| Former path | Replacement |
|-------------|-------------|
| Root `init-roles.yaml` | `playbooks/init_nodes.yaml` via `./run.sh` |
| `group_vars/all/standalone.example.yml` | knobs live in `group_vars/all/atlas-node-foundation.yml` (+ optional `examples/secrets.example.yml`) |
| `roles/13_configure_repo/files/*.{sources,repo}` | Jinja templates under `roles/13_configure_repo/templates/` |

## Integrations

**Standalone:** `./run.sh` with local `inventory.yml` + `group_vars/all/atlas-node-foundation.yml`.

**atlas-clusterctl:** materialize this repo next to the controller (`source: local`,
`path_relative_to: sibling`) or via `./cluster repos sync`. Typical phases:
`atlas-node-foundation/init-infra` and `atlas-node-foundation/init`. Targeting and vars come from
the cluster leaf (`hosts`, `group_vars`); set `node_foundation_init_hosts` to the inventory groups
you want prepared.

## Security

See [`SECURITY.md`](SECURITY.md) for reporting and secret-handling guidance. Do not commit real
bootstrap passwords, vault files, SSH private keys, or live inventories (`inventory.yml` / local
`hosts` are gitignored).

Pre-publish checklist (index gates, push dry-run, history rewrite):
[`docs/pre-publish.md`](docs/pre-publish.md).

## Contributing

1. Keep `playbooks/init_nodes.yaml` as the only supported playbook entry.
2. Follow role naming `##_role_name`; document knobs in `group_vars/all/atlas-node-foundation.yml` and role defaults.
3. Extend `tests/` for layout / contract changes.
4. Run `./tests/run_ci.sh` before proposing changes.
5. Keep product paths free of live secrets and org fingerprints (`CHANGEME` / `example.com`).
6. Before a public remote, follow [`docs/pre-publish.md`](docs/pre-publish.md).
7. Update this README when tags, targeting, or runner behaviour change.

## Support

Open an issue in the repository for bugs and questions.
