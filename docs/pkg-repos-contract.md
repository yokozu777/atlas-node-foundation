# Package repos — Phase 0 contract (locked)

**Status:** Phase 0 locked · Phase 1 catalog complete · Phases 2–6 done · **Waves A–D post-Phase-6 hardening (2026-07-30)**  
**Scope:** client config for `atlas-node-foundation` role `13_configure_repo`, plus cross-repo boundaries.  
**Migration:** greenfield only (wipe + redeploy). No in-place node file migrate. No compatibility shim.

Runtime implements this contract in role `13_configure_repo`. Inventory / `_template`
foundation overlays use `pkg_repos` (and optional leaf `pkg_repos_extra`) (**Phase 5**).
Env/default may hold OS base `pkg_repos`; stack leaves append via `pkg_repos_extra`
(concat at role start). Infra nginx **warm** cache still gates on `enable_repo_*` in
`atlas-infra-edge.yml` (not the client write path).
Phase 6 locks publish surfaces: drift catalog↔infra, client-path grep-gates, greenfield checklist.
Waves A–D harden safety (cleanup), template/inventory consistency, medium debt, and docs.

**Sources of truth (do not confuse):**
- Client lists / catalog / contract → this repo + `atlas-inventory/clusters/**` + `atlas-clusterctl/clusters/_template/**`
- Infra upstreams / warm → `atlas-infra-edge` (+ inventory `atlas-infra-edge.yml` overlays)
- Durable Terraform state trees (`tfstate-repo/`, inventory `tfstate/`) are **not** package-repo SoT

Official upstream URL table: [`pkg-repos-catalog.md`](pkg-repos-catalog.md) /
[`pkg-repos-catalog.yml`](pkg-repos-catalog.yml).

---

## Goals

1. Operator-facing lists: which repos are enabled and which URI apt/yum uses.
2. Different clusters ⇒ different effective lists (postgresql ≠ redis ≠ k8s), via full
   `pkg_repos` and/or shared base + `pkg_repos_extra`.
3. Mirror metadata (`upstream_url` / `upstream_host`) lives only in **atlas-infra-edge**.
4. Remove org filename prefix knobs; file/section names come from `name`.

---

## Client schema (target)

```yaml
# Site / org (once) or leaf override
pkg_repo_base: "https://nexus.example.com/repository"

# Optional — wipe managed drop-ins before write.
# MUST be false (or omit) when the combined list is empty; role asserts otherwise.
cleanup_repositories: true

# Base repos (env default and/or leaf). Role may also append pkg_repos_extra.
pkg_repos:
  - name: ubuntu                 # slug (see catalog)
    enabled: true
    uri: "{{ pkg_repo_base }}/ubuntu"

# Optional stack extras (same schema). Concatenated onto pkg_repos at role start.
# Prefer this on inventory leaves when OS base lives in <env>/default.
pkg_repos_extra:
  - name: pgdg-apt
    enabled: true
    uri: "{{ pkg_repo_base }}/pgdg-apt"
```

### Field rules

| Field | Rule |
|-------|------|
| `name` | Stable slug from [`pkg-repos-catalog.md`](pkg-repos-catalog.md). Unique across **combined** `pkg_repos` + `pkg_repos_extra`. |
| `enabled` | `true` → write drop-in; `false` → omit (or remove if cleanup). |
| `uri` | **Exact** string written to apt `URIs:` / yum `baseurl=` (no client-side mode resolver). |
| `pkg_repo_base` | Convenience for Nexus path composition only. Not required if every `uri` is absolute. |
| `pkg_repos_extra` | Optional; same item schema as `pkg_repos`. Appended in `13_configure_repo` before validate/apply. |

### URI policy (locked)

- Leaf always stores a **full** `uri` (what the node will fetch).
- **Nexus (org default):** `uri: "{{ pkg_repo_base }}/{{ name }}"`.
- **Nginx pkg-repo mirror:** prefer `uri: "{{ name | pkg_repo_nginx_uri(pkg_repo_nginx_domain) }}"` (host slugbing: non `[a-zA-Z0-9._-]` → `-`, then `.` → `-`). Equivalent inline Jinja: `https://{{ name | regex_replace('[^a-zA-Z0-9._-]', '-') | regex_replace('\\.', '-') }}.{{ pkg_repo_nginx_domain }}`.  
  Prefer writing the concrete URI / filter call on the leaf/template rather than re-introducing a client `mode` enum.
- **No per-item “sometimes public” escape** in the contract. Org uses one mirror strategy; changing strategy means changing `pkg_repo_base` / URIs on leaves (or site overlay), not a second resolver.

### On-disk names (locked)

Derived **only** from `name` (no `pkg_repo_name_prefix`):

| Kind | Path / id |
|------|-----------|
| APT sources | `/etc/apt/sources.list.d/{{ name }}.sources` |
| YUM repo file | `/etc/yum.repos.d/{{ name }}.repo` |
| YUM section id | `[{{ name }}]` |

One logical repo ⇒ one drop-in file (split today’s composite `debian.sources` / `oracle9.repo` multi-section files in Phase 2).

### Related knobs that stay (not part of the list)

| Knob | Owner | Why |
|------|-------|-----|
| `pgsql_version` | postgresql overlay (`atlas-postgresql.yml`) | Major version segment under PGDG yum tree when rendering `pgdg-yum` content (not a substitute for `uri`). **SoT on the product overlay only** — do not also set it on `atlas-node-foundation.yml` (avoids 16/18 conflicts). Role default is `18` if unset. |
| `cleanup_repositories` | foundation | Whether to clear managed drop-ins before apply. **Must not** be `true` when combined `pkg_repos` (+ `pkg_repos_extra`) is empty (role asserts; would wipe apt/yum and write nothing). |
| `oracle_bootstrap_epel_*` | foundation network handoff | Temporary bootstrap repo; fixed path `atlas-bootstrap-OL-developer-EPEL.repo` (no org prefix). |
| `pkg_repo_apt_acquire_by_hash` | foundation | Optional APT `Acquire::By-Hash` drop-in when uris use nginx mirrors. |

---

## Infra boundary (locked)

| Concern | Repo / file |
|---------|-------------|
| Client enable + URI | `atlas-node-foundation` `pkg_repos` (+ optional `pkg_repos_extra`) |
| Mirror pull / nginx `Host` + SNI (`upstream_host`) | `atlas-infra-edge` `pkg_repo_upstreams` only |
| Harbor registry hostname | `atlas-infra-edge` (`harbor_host`) — **not** package repos |
| Official URL documentation | [`pkg-repos-catalog.md`](pkg-repos-catalog.md) |

`slug` in infra `pkg_repo_upstreams` **must equal** client `name`.

**Phase 3 done:** infra `pkg_repo_upstreams` includes `pgdg-apt` / `pgdg-yum`; mirror enable is `setup_pkg_repo_nginx` (not derived from client `use_internal_rpm_apt_repo`).

---

## Per-cluster lists (examples)

| Leaf | Typical `name`s |
|------|-----------------|
| `postgresql` | `ubuntu`, `debian-main`, `debian-security`, `pgdg-apt`, `OL9_baseos`, `OL9_appstream`, `OL9_developer_EPEL`, `OL9_codeready_builder` (+ `pgdg-yum` on Oracle guests) |
| `redis` / `kafka` | Mixed-OS base: `ubuntu`, `debian-main`, `debian-security`, `OL9_*` — **no** PGDG/containerd |
| `jenkins_agent` | OS + `yum_docker-ce-stable-9` (or 10) as required |
| `k8s_full` | OS + `ubuntu-containerd` / `debian-containerd` + `k8s-ubuntu-<ver>` / `k8s-<ver>` |
| `infra_edge` (node foundation) | OS + docker yum as required; URIs point at chosen mirror |
| `infra_edge` (mirror warm) | Superset for site guests — see catalog `example_leaf_lists.infra_mirror_*` |

Exact lists live in inventory / `_template` (Phase 5) and are sketched in
[`pkg-repos-catalog.yml`](pkg-repos-catalog.yml) `example_leaf_lists`.

---

## Deprecated (remove in Phase 2–5; do not use in new overlays)

### Client / foundation

- `pkg_repo_name_prefix`
- `use_internal_rpm_apt_repo` (client path)
- `nexus_base_url` / `nexus_host` on foundation leaves → replace with `pkg_repo_base` or full `uri`
- `pkg_repo_nginx_ingress_domain` on foundation leaves → bake into `uri` or site helper only for rendering templates
- `enable_repo_*` (all)
- `install_managed_pkg_repos`
- `install_k8s_pkg_repo`
- `install_additional_repos` (if solely used to gate managed OS repos)
- `pkg_repo_upstreams` on node-foundation / stack foundation overlays
- `pkg_repo_managed_*` path vars derived from prefix
- `pkg_repo_client_uri` as the **client** write path (removed; use leaf `uri` or helper `pkg_repo_nginx_uri`)
- `harbor_host` in `atlas-node-foundation.yml` overlays

### Cross-repo follow-ups (Phase 4) — **done**

- ~~`atlas-postgresql`: `pkg_repo_name_prefix` + paths → expect `/etc/apt/sources.list.d/pgdg-apt.sources` (and yum `pgdg-yum.repo`) when `pgsql_pgdg_repo_from_init: true`~~
- ~~`atlas-jenkins-agent` / `atlas-k8s-core`: drop client dependency on `use_internal_rpm_apt_repo`~~ — URI bake: `pkg_repo_base` → `pkg_repo_nginx_ingress_domain` → public; prefer foundation catalog drop-ins when present
- `atlas-infra-edge`: ~~replace derived use of `use_internal_rpm_apt_repo` for mirror enable~~ **done (Phase 3)** — `setup_pkg_repo_nginx` / `setup_apt_rpm_nginx`

---

## Phase map (reminder)

| Phase | Work |
|-------|------|
| **0** | This contract — **done** |
| **1** | Official URL catalog (YAML + MD), consumers, infra gaps — **done** |
| **2** | Implement foundation hard cut — **done** |
| **3** | Infra upstreams SoT + mirror knobs; add PGDG upstreams — **done** |
| **4** | Sibling products (postgresql, jenkins, k8s) — **done** |
| **5** | Inventory + `_template` per-leaf lists — **done** |
| **6** | Publish, greenfield smoke, grep-gates, docs↔upstreams drift check — **done** |

---

## Acceptance (Phase 0)

- [x] Client schema and URI/file naming locked in this file  
- [x] Full slug ↔ official URL catalog exists (Phase 1 YAML + MD)  
- [x] Infra vs client boundary and deprecated list written  
- [x] Per-cluster list principle stated  
- [x] Greenfield / no-shim migration assumption stated  

## Acceptance (Phase 2)

- [x] Role `13_configure_repo` writes `/etc/apt/sources.list.d/{{ name }}.sources` and `/etc/yum.repos.d/{{ name }}.repo` from `pkg_repos`  
- [x] `uri` written verbatim (no client mode resolver)  
- [x] Legacy `enable_repo_*` / `pkg_repo_name_prefix` / `use_internal_rpm_apt_repo` removed from role + product group_vars  
- [x] One logical repo ⇒ one drop-in; composite templates removed  
- [x] Oracle bootstrap EPEL uses fixed `atlas-bootstrap-OL-developer-EPEL.repo`  
- [x] Unit tests gate filter resolve + role layout (`tests/test_pkg_repos_phase2.py`)

## Acceptance (Phase 4)

- [x] `atlas-postgresql` expects catalog `pgdg-apt.sources` / `pgdg-yum.repo` (no `pkg_repo_name_prefix`)
- [x] `atlas-jenkins-agent` / `atlas-k8s-core` drop `use_internal_rpm_apt_repo`; URI via `pkg_repo_uri` (`base` → domain → public)
- [x] Prefer foundation catalog drop-ins when present; sibling writes matching catalog filenames otherwise
- [x] Product layout/filter tests + inventory/template sibling overlays updated

## Acceptance (Phase 5)

- [x] Inventory + `_template` `atlas-node-foundation.yml` use `pkg_repos[{name,enabled,uri}]`
- [x] Foundation client overlays drop `enable_repo_*`, `pkg_repo_name_prefix`, `use_internal_rpm_apt_repo`, `pkg_repo_upstreams`, `pkg_repo_managed_*`, `harbor_host`
- [x] Enabled names match catalog `example_leaf_lists` for known foundation leaves
- [x] Nexus leaves: `uri: "{{ pkg_repo_base }}/{{ name }}"`; nginx leaves: baked `https://<slug>.<domain>` (prefer `pkg_repo_nginx_uri`)
- [x] Infra-edge **warm** may still use `enable_repo_*` (client path is independent)
- [x] Gates: `tests/test_pkg_repos_phase5.py`
- [x] **Wave A:** `cleanup_repositories=true` requires non-empty combined `pkg_repos` (+ `pkg_repos_extra`); k8s leaf / `_template/k8s_full` no longer ship cleanup∧empty
- [x] **Wave B:** `_template/infra_edge` warms PGDG; nginx NF URIs use `pkg_repo_nginx_uri`; `pgsql_version` SoT only on `atlas-postgresql.yml` for postgresql leaves
- [x] **Wave C:** drop dead `pkg_repo_managed_*` on infra overlays; jenkins fallback writes Deb822 `.sources`; jenkins NF includes containerd; `debian-non-free` template uses real contrib/non-free components

## Acceptance (Phase 6)

- [x] Catalog ↔ infra `pkg_repo_upstreams` drift gate (product + inventory leaves)
- [x] Warm `enable_repo_*: true` set ↔ `example_leaf_lists.infra_mirror_*` (inventory)
- [x] Grep-gates: no legacy client knobs on NF overlays / product overlays / sibling product catalogs
- [x] Infra mirror gate formula: `setup_apt_rpm_nginx` follows `setup_pkg_repo_nginx` (not client mode)
- [x] Greenfield smoke checklist documented below (live labs offline-optional)
- [x] Publish surfaces: CHANGELOG + README Phase 0–6; gates `tests/test_pkg_repos_phase6.py`

## Greenfield smoke

Wipe + redeploy only (no in-place node migrate). Offline CI covers unit/layout gates; live checks:

1. **Infra first** — deploy `atlas-infra-edge` with `setup_pkg_repo_nginx: true`; confirm warm covers site `example_leaf_lists.infra_mirror_*` (incl. PGDG on `_template/infra_edge`).
2. **Init** — run `atlas-node-foundation` `13_configure_repo` on a leaf whose **combined**
   `pkg_repos` + `pkg_repos_extra` is non-empty (role sets `_pkg_repos_effective`).
   Never ship `cleanup_repositories: true` with both lists empty (role fails; would wipe
   apt/yum and write nothing). Env default may hold OS base; stack leaves may only set
   `pkg_repos_extra`.
3. **Drop-ins** — on each guest OS, expect `/etc/apt/sources.list.d/{{ name }}.sources` or `/etc/yum.repos.d/{{ name }}.repo` for enabled applicable names; `uri` verbatim (nginx leaves: `pkg_repo_nginx_uri` slugbing).
4. **k8s leaves** — k8s inventory leaf (e.g. `dev/k8s`) and `_template/k8s_full` must list OS + containerd + `k8s-ubuntu-<ver>` / `k8s-<ver>` + OL Docker/base (see `example_leaf_lists.foundation_dev/k8s` / `foundation_k8s_full`; legacy catalog key `foundation_dev/mxhash`). Do not rely on k8s-core fallback alone for base OS repos.
5. **PGDG** — postgresql leaf with `pgsql_pgdg_repo_from_init: true` → `pgdg-apt.sources` / `pgdg-yum.repo` present before `201_pgsql_cluster`. `pgsql_version` SoT is `atlas-postgresql.yml` only.
6. **Siblings** — jenkins/k8s prefer foundation drop-ins; if absent, URI bake via `pkg_repo_base` → nginx domain → public (Deb822 `.sources`, same catalog names).
7. **No shim** — do not keep `{prefix}-*.sources` alongside catalog names on the same node.

## Acceptance (Wave D — docs / publish)

- [x] Contract status + SoT boundaries (inventory/`_template` vs `tfstate-repo`) documented
- [x] Greenfield checklist covers cleanup⇒non-empty, k8s/`foundation_dev/k8s` (legacy `foundation_dev/mxhash`), PGDG version SoT
- [x] Catalog MD phase checklist includes post-Phase-6 Waves A–D; no stale “empty pkg_repos” guidance in stack docs
- [x] CHANGELOG / README publish surfaces mention Waves A–D hardening
- [x] Gates: `tests/test_pkg_repos_phase6.py` (greenfield + stack-doc anti-stale)

## Deferred / known gaps

- **APT keyrings still fetched from public URLs** (PGDG / Docker / k8s `get_url` in `13_configure_repo`, and jenkins/k8s fallbacks). Package indexes can be mirrored; key material is not yet on the same mirror policy. Follow-up: catalog `key_uri` / mirror path, or document air-gap key bootstrap — do not silently change key sources without an ADR.
