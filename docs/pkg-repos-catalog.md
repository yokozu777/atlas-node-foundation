# Package repos catalog — official upstream URLs

**Status: Phase 1 SoT complete · Phases 2–6 done · Waves A–D hardening (2026-07-30)**  
**Structured SoT:** [`pkg-repos-catalog.yml`](pkg-repos-catalog.yml) (prefer for automation / drift gates)  
**Client contract:** [`pkg-repos-contract.md`](pkg-repos-contract.md)

This document is the human view of every supported `name` / `slug`, its **official**
public upstream URL, and the host nginx must send as `Host` / TLS SNI when mirroring.

| Layer | Uses |
|-------|------|
| Client leaf `pkg_repos[].name` | Must be a catalog `name` (or k8s pattern below) |
| Client `uri` (Nexus) | Usually `{{ pkg_repo_base }}/{{ name }}` |
| Infra `pkg_repo_upstreams` | Same `slug` + `upstream_url` / `upstream_host` from this catalog |

---

## APT (Debian / Ubuntu / PGDG / containerd / k8s deb)

| name | Official upstream URL | upstream_host | Target drop-in | Infra mirror |
|------|----------------------|---------------|----------------|--------------|
| `debian-main` | `https://deb.debian.org/debian` | `deb.debian.org` | `debian-main.sources` | present |
| `debian-security` | `https://deb.debian.org/debian-security` | `deb.debian.org` | `debian-security.sources` | present |
| `debian-non-free` | `https://deb.debian.org/debian` | `deb.debian.org` | `debian-non-free.sources` | present |
| `ubuntu` | `https://archive.ubuntu.com/ubuntu` | `archive.ubuntu.com` | `ubuntu.sources` | present |
| `debian-containerd` | `https://download.docker.com/linux/debian` | `download.docker.com` | `debian-containerd.sources` | present |
| `ubuntu-containerd` | `https://download.docker.com/linux/ubuntu` | `download.docker.com` | `ubuntu-containerd.sources` | present |
| `pgdg-apt` | `https://apt.postgresql.org/pub/repos/apt` | `apt.postgresql.org` | `pgdg-apt.sources` | present |
| `gitlab-runner-ubuntu` | `https://packages.gitlab.com/runner/gitlab-runner/ubuntu` | `packages.gitlab.com` | `gitlab-runner.sources` (atlas-gitlab-runner) | present |
| `gitlab-runner-debian` | `https://packages.gitlab.com/runner/gitlab-runner/debian` | `packages.gitlab.com` | `gitlab-runner.sources` (atlas-gitlab-runner) | present |
| `k8s-ubuntu-<ver>` | `https://pkgs.k8s.io/core:/stable:/v<ver>/deb/` | `pkgs.k8s.io` | `k8s-ubuntu-<ver>.sources` | present (templated) |

Signing (typical): Debian/Ubuntu archive keyrings; PGDG → `/usr/share/keyrings/postgresql.gpg`.  
PGDG suite: `{{ ansible_distribution_release }}-pgdg`.  
`debian-non-free` Deb822 uses Components `contrib non-free non-free-firmware` (bookworm+).

---

## YUM (Docker / PGDG / Oracle / k8s rpm)

| name | Official upstream URL | upstream_host | Target drop-in | Infra mirror |
|------|----------------------|---------------|----------------|--------------|
| `yum_docker-ce-stable-9` | `https://download.docker.com/linux/centos/9/x86_64/stable` | `download.docker.com` | `yum_docker-ce-stable-9.repo` | present |
| `yum_docker-ce-stable-10` | `https://download.docker.com/linux/centos/10/x86_64/stable` | `download.docker.com` | `yum_docker-ce-stable-10.repo` | present |
| `pgdg-yum` | `https://download.postgresql.org/pub/repos/yum` | `download.postgresql.org` | `pgdg-yum.repo` | present |
| `gitlab-runner-el` | `https://packages.gitlab.com/runner/gitlab-runner/el/9/x86_64` | `packages.gitlab.com` | `gitlab-runner.repo` (atlas-gitlab-runner) | present |
| `k8s-<ver>` | `https://pkgs.k8s.io/core:/stable:/v<ver>/rpm/` | `pkgs.k8s.io` | `k8s-<ver>.repo` | present (templated) |
| `OL9_baseos` | `https://yum.oracle.com/repo/OracleLinux/OL9/baseos/latest/x86_64/` | `yum.oracle.com` | `OL9_baseos.repo` | present |
| `OL9_appstream` | `https://yum.oracle.com/repo/OracleLinux/OL9/appstream/x86_64/` | `yum.oracle.com` | `OL9_appstream.repo` | present |
| `OL9_addons` | `https://yum.oracle.com/repo/OracleLinux/OL9/addons/x86_64/` | `yum.oracle.com` | `OL9_addons.repo` | present |
| `OL9_developer` | `https://yum.oracle.com/repo/OracleLinux/OL9/developer/x86_64/` | `yum.oracle.com` | `OL9_developer.repo` | present |
| `OL9_developer_EPEL` | `https://yum.oracle.com/repo/OracleLinux/OL9/developer/EPEL/x86_64/` | `yum.oracle.com` | `OL9_developer_EPEL.repo` | present |
| `OL9_codeready_builder` | `https://yum.oracle.com/repo/OracleLinux/OL9/codeready/builder/x86_64/` | `yum.oracle.com` | `OL9_codeready_builder.repo` | present |
| `OL9_kvm` | `https://yum.oracle.com/repo/OracleLinux/OL9/kvm/utils/x86_64/` | `yum.oracle.com` | `OL9_kvm.repo` | present |
| `OL9_MODRHCK` | `https://yum.oracle.com/repo/OracleLinux/OL9/MODRHCK/x86_64/` | `yum.oracle.com` | `OL9_MODRHCK.repo` | present |
| `OL9_oraclelinuxmanager210` | `https://yum.oracle.com/repo/OracleLinux/OL9/oraclelinuxmanager210/client/x86_64/` | `yum.oracle.com` | `OL9_oraclelinuxmanager210.repo` | present |
| `OL9_RDMA` | `https://yum.oracle.com/repo/OracleLinux/OL9/RDMA/x86_64/` | `yum.oracle.com` | `OL9_RDMA.repo` | present |
| `OL9_UEKR7` | `https://yum.oracle.com/repo/OracleLinux/OL9/UEKR7/x86_64/` | `yum.oracle.com` | `OL9_UEKR7.repo` | present |
| `OL9_UEKR8` | `https://yum.oracle.com/repo/OracleLinux/OL9/UEKR8/x86_64/` | `yum.oracle.com` | `OL9_UEKR8.repo` | present |
| `OL10_baseos` | `https://yum.oracle.com/repo/OracleLinux/OL10/baseos/latest/x86_64/` | `yum.oracle.com` | `OL10_baseos.repo` | present |
| `OL10_appstream` | `https://yum.oracle.com/repo/OracleLinux/OL10/appstream/x86_64/` | `yum.oracle.com` | `OL10_appstream.repo` | present |
| `OL10_addons` | `https://yum.oracle.com/repo/OracleLinux/OL10/addons/x86_64/` | `yum.oracle.com` | `OL10_addons.repo` | present |
| `OL10_developer` | `https://yum.oracle.com/repo/OracleLinux/OL10/developer/x86_64/` | `yum.oracle.com` | `OL10_developer.repo` | present |
| `OL10_developer_EPEL` | `https://yum.oracle.com/repo/OracleLinux/OL10/0/developer/EPEL/x86_64/` | `yum.oracle.com` | `OL10_developer_EPEL.repo` | present |
| `OL10_RDMA` | `https://yum.oracle.com/repo/OracleLinux/OL10/RDMA/x86_64/` | `yum.oracle.com` | `OL10_RDMA.repo` | present |
| `OL10_UEKR8` | `https://yum.oracle.com/repo/OracleLinux/OL10/UEKR8/x86_64/` | `yum.oracle.com` | `OL10_UEKR8.repo` | present |
| `OL10_builder` | `https://yum.oracle.com/repo/OracleLinux/OL10/distro/builder/x86_64/` | `yum.oracle.com` | `OL10_builder.repo` | present |

`pgdg-yum` content path under the upstream (and usually under Nexus slug root):  
`/{{ pgsql_version }}/redhat/rhel-{{ ansible_distribution_major_version }}-x86_64/`.

---

## K8s versioned names

Inventory sets `k8s_apt_repo_version` (e.g. `1.36`). Concrete names:

| Pattern | Example name | Example official URL |
|---------|--------------|----------------------|
| `k8s-ubuntu-<ver>` | `k8s-ubuntu-1.36` | `https://pkgs.k8s.io/core:/stable:/v1.36/deb/` |
| `k8s-<ver>` | `k8s-1.36` | `https://pkgs.k8s.io/core:/stable:/v1.36/rpm/` |

Infra already templates these in `pkg_repo_upstreams`.

---

## Stack / leaf guidance (different clusters ⇒ different lists)

Two different inventories must not be conflated:

| Surface | File | Status (Phase 5) |
|---------|------|------------------|
| **Foundation client** | leaf / env `atlas-node-foundation.yml` | **`pkg_repos`** + optional **`pkg_repos_extra`** (done) |
| **Infra mirror warm** | leaf `atlas-infra-edge.yml` `enable_repo_*` | still gates nginx warm pull (client path independent) |

Mapped from former inventory `enable_repo_*: true` → catalog names.
Only **enabled** names belong on the foundation client surface. Role
`13_configure_repo` combines `pkg_repos` + `pkg_repos_extra` into
`_pkg_repos_effective` (does not mutate the source lists).

### Foundation clients (`pkg_repos` / `pkg_repos_extra`)

Live inventory gates use `foundation_dev/*`. Keys `foundation_ci/*` are
template / historical compact guidance (align with `_template` leaves).

| Leaf | Target `name`s |
|------|----------------|
| `dev/postgresql`, `lab/pgsql`, `_template/postgresql` | OS base (+ env default) + `pgdg-apt` / `pgdg-yum` (often via `pkg_repos_extra`) |
| `dev/redis`, `dev/kafka`, `lab/kafka`, `_template/redis|kafka` | mixed-OS base (`example_leaf_lists.foundation_dev/redis`; compact `foundation_ci/*` for templates) |
| `dev/jenkins`, `dev/gitlab` | OS base + containerd + Docker CE yum extras |
| `dev/infra` | OS base + containerd/docker extras as needed |
| `dev/k8s`, `_template/k8s_full` | Debian/Ubuntu (+ containerd), `k8s-ubuntu-1.36`, `k8s-1.36`, Docker CE 9/10, OL9/OL10 + UEK (`example_leaf_lists.foundation_dev/k8s` / `foundation_k8s_full`; legacy key `foundation_dev/mxhash`) |

Legacy `enable_repo_pgdg: true` ⇒ enable **`pgdg-apt` on Debian/Ubuntu guests** and **`pgdg-yum` on Oracle guests** (both names listed on mixed leaves; role writes the matching OS drop-in).

### Infra mirror warm (site-wide)

Infra and k8s leaves warm a **superset** so every guest distro can resolve through nginx: Debian/Ubuntu (+ containerd), PGDG apt/yum, k8s apt/yum `1.36`, Docker CE 9/10, OL9/OL10 baseos/appstream/EPEL + OL9 CRB + UEK modules.

Full `legacy_enable_map` and `example_leaf_lists` (including `infra_mirror_*` keys): see YAML SoT.

---

## Infra coverage (Phase 3)

| name | In catalog | In `atlas-infra-edge` `pkg_repo_upstreams` |
|------|------------|---------------------------------------------|
| `pgdg-apt` | yes | **yes** |
| `pgdg-yum` | yes | **yes** |
| All other static rows above | yes | yes (URL match expected) |
| k8s templated rows | yes (pattern) | yes |

PGDG warm uses `enable_repo_pgdg_apt` / `enable_repo_pgdg_yum` (or legacy `enable_repo_pgdg`).

---

## Drift rules

1. **YAML first:** add/change a repo in `pkg-repos-catalog.yml`, then refresh this MD if tables change.  
2. **Infra second:** add/update `pkg_repo_upstreams` with the same `slug`, `upstream_url`, `upstream_host`.  
3. **Clients third:** leaf `pkg_repos[].name` must exist here.  
4. Phase 6 gate (**done**): every infra static upstream URL ⊆ this catalog; every `infra_mirror: present` row must exist in infra (`tests/test_pkg_repos_phase6.py`).

---

## Phase 1 acceptance

- [x] Every static infra `pkg_repo_upstreams` slug has a catalog row with matching URL/host  
- [x] Every catalog `infra_mirror: present` row exists in infra  
- [x] PGDG rows exist in catalog (marked `present` after Phase 3)  
- [x] `legacy_enable_map` covers inventory foundation/infra enable flags (incl. k8s 1.36 examples)  
- [x] `example_leaf_lists` covers foundation clients + infra warm sets  
- [x] MD tables list every YAML `official_url`  
- [x] Unit tests gate the above (`tests/test_pkg_repos_phase1_catalog.py`)

## Phase checklist

| Phase | Catalog / contract work | Status |
|-------|-------------------------|--------|
| **0** | Seed contract + initial MD | done |
| **1** | Full official URL SoT (YAML + MD), consumers, infra gaps | **done** (Phase 1 complete) |
| **2** | Foundation hard cut (`pkg_repos` runtime) | **done** |
| **3** | Add PGDG upstreams + infra-local mirror gate | **done** |
| **4** | Sibling products (postgresql, jenkins, k8s) | **done** |
| **5** | Inventory + `_template` per-leaf `pkg_repos` | **done** |
| **6** | Automated drift gate docs ↔ infra + grep-gates | **done** |
| **A–D** | Post-Phase-6 hardening (cleanup safety, template PGDG/nginx/`pgsql_version`, jenkins Deb822, docs/SoT) | **done** |
