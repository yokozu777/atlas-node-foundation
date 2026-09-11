# Changelog

## [Unreleased]

### Added
- `12_date_timezone`: `ntp_manage_host_chrony` (default true). When false,
  apply timezone only and skip host chrony / offset assert — for leaves where
  another stack owns the clock (e.g. atlas-infra-edge NTP compose).
  `timedatectl set-ntp` runs only when `timedatectl show -p CanNTP` is `yes`
  (avoids hard-fail `NTP not supported` on masked chrony / no timesyncd).
- `16_configure_bash`: `bash_export_locale` (default true). When false, skip
  `export LANG`/`LC_ALL` in `/etc/profile` (use with `configure_locales: false`
  to avoid login `setlocale` warnings when the locale is not generated).
- `pkg_repos_extra`: stack/site list concatenated with `pkg_repos` in role
  `13_configure_repo` as `_pkg_repos_effective` (idempotent; does not mutate
  `pkg_repos`). Env default may hold OS base; leaves add extras only.

### Changed
- Catalog `example_leaf_lists` for `foundation_ci/{kafka,redis}` and
  `foundation_lab/kafka`: mixed-OS base set (ubuntu + debian-main/security +
  OL9_*), aligned with inventory Phase 0/1 SoT
  (`clusters/ci/MIXED_OS_KAFKA_REDIS.md`). Contract sketch for redis/kafka
  leaf lists updated accordingly.

### Fixed

- `04_configure_hostname`: restart `systemd-networkd` only when the unit is
  already present in `service_facts` (OL installs networkd later in
  `17_configure_network`). Avoids noisy ignored fatals on fresh oracle-base.
- `11_certificates`: always re-fetch CA via `get_url` (`force: true`) and replace
  the dest file when checksum/content changes; refresh trust with
  `update-ca-certificates --fresh` (Debian/Ubuntu) or `update-ca-trust extract`
  (Oracle). Avoids leaf hosts keeping a stale root after step-ca recreate.
  Oracle URL CA path now uses `/etc/pki/ca-trust/source/anchors/` (replace by
  name) instead of add-only `trust anchor --store`.

### Added (pkg repos — Phase 0)

- Locked client package-repo contract and official upstream catalog:
  `docs/pkg-repos-contract.md`, `docs/pkg-repos-catalog.md`.
- Target schema: `pkg_repo_base` + `pkg_repos[{name,enabled,uri}]`; file names from
  `name`; mirror `upstream_host` stays in atlas-infra-edge. Greenfield hard cut
  (no shim). Runtime implemented in Phase 2 (`pkg_repos` list).

### Added (pkg repos — Phase 1)

- Structured catalog SoT `docs/pkg-repos-catalog.yml` (official URLs, drop-ins,
  infra mirror coverage, legacy enable map, example leaf lists).
- Expanded `docs/pkg-repos-catalog.md` with foundation vs infra-warm consumer
  matrices and PGDG infra gaps.
- Drift gates: `tests/test_pkg_repos_phase1_catalog.py` (catalog shape, MD sync,
  infra URL match when sibling present, inventory enable-flag coverage).

### Changed (pkg repos — Phase 2)

- Hard cut `roles/13_configure_repo` to `pkg_repo_base` + `pkg_repos[{name,enabled,uri}]`.
- One drop-in per name (`{{ name }}.sources` / `{{ name }}.repo`); `uri` written verbatim.
- Removed client mode resolver (`pkg_repo_client_uri`), `enable_repo_*`,
  `pkg_repo_name_prefix`, `install_managed_pkg_repos`, composite templates.
- Filter helpers: `pkg_repo_resolve` / `pkg_repo_enrich` / `pkg_repo_nginx_uri`.
- Oracle bootstrap EPEL fixed at `atlas-bootstrap-OL-developer-EPEL.repo`.
- Gates: `tests/test_pkg_repos_phase2.py`. Inventory leaf migration remains Phase 5.

### Changed (pkg repos — Phase 3)

- Catalog marks `pgdg-apt` / `pgdg-yum` as `infra_mirror: present`; example warm
  lists include PGDG; contract Phase 3 marked done.

### Changed (pkg repos — Phase 4)

- Sibling hard cut documented in contract: postgresql catalog PGDG paths;
  jenkins-agent / k8s-core use `pkg_repo_uri` (`pkg_repo_base` → nginx domain →
  public), no `use_internal_rpm_apt_repo` on the product client path.

### Changed (pkg repos — Phase 5)

- Inventory + `_template` foundation overlays migrate to `pkg_repos` lists
  (Nexus `pkg_repo_base` or nginx-baked URIs). Legacy client knobs removed from
  NF overlays. Infra warm `enable_repo_*` on `atlas-infra-edge.yml` retained.
- Gates: `tests/test_pkg_repos_phase5.py`.

### Changed (pkg repos — Phase 6)

- Publish close-out: catalog↔infra drift gates, warm-set parity with
  `example_leaf_lists.infra_mirror_*`, client-path grep-gates, greenfield smoke
  checklist in the contract. Gates: `tests/test_pkg_repos_phase6.py`.

### Fixed (pkg repos — Wave A)

- Role `13_configure_repo` asserts and skips wipe when
  `cleanup_repositories=true` with empty `pkg_repos` (would leave nodes without
  apt/yum sources). Post-cleanup yum applicability assert added.
- `dev/mxhash` and `_template/k8s_full` foundation overlays get full guest
  `pkg_repos` lists; catalog `example_leaf_lists` + phase5 gates updated.

### Fixed (pkg repos — Wave B)

- `_template/infra_edge` warms PGDG (`enable_repo_pgdg_*` + `pgdg-apt`/`pgdg-yum`
  upstreams); phase6 gates template warm/upstream parity with catalog.
- Nginx foundation leaves (`ci/infra`, `_template/infra_edge`) bake URIs via
  `pkg_repo_nginx_uri` and `repo.{{ dns_domain_suffix }}`.
- `pgsql_version` SoT only on `atlas-postgresql.yml` for lab/pgsql and
  `_template/postgresql` (removed conflicting foundation `18` vs product `16`).

### Fixed (pkg repos — Wave C)

- `debian-non-free` Deb822 template: suites `release`/`release-updates`,
  components `contrib non-free non-free-firmware` (was broken `main`-only).
- Jenkins / template jenkins_agent foundation lists include
  `ubuntu-containerd` / `debian-containerd`.
- APT key mirroring deferred (see contract Deferred / known gaps).

### Changed (pkg repos — Wave D)

- Contract/catalog publish polish: SoT boundaries (inventory/`_template` vs
  `tfstate-repo`), greenfield checklist (cleanup⇒non-empty, mxhash/k8s_full),
  phase checklist Waves A–D. Stack docs no longer advertise empty k8s
  `pkg_repos`. Gates extended in `tests/test_pkg_repos_phase6.py`.

### Fixed (pkg repos — post-Wave D)

- Cleanup gate now rglob’s all `clusters/**/atlas-node-foundation.yml` (incl.
  shared `_template/group_vars` stub).
