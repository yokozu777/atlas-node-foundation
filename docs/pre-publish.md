# Pre-publish checklist (`atlas-node-foundation`)

Operator checklist before opening a **public** remote. This does **not** rewrite git
history — that is a separate, destructive step after the working tree is green.

Companion: [`SECURITY.md`](../SECURITY.md), [`./tests/run_ci.sh`](../tests/run_ci.sh).

## Status of publish steps 0–6

| Step | Focus | Expectation before this checklist |
|------|--------|-----------------------------------|
| 0 | Hygiene + ignore | `inventory.yml` / `hosts` / `secrets.yml` / `workspace/` / `pub_keys/` gitignored |
| 1 | Scrub product | `CHANGEME` / `example.com` in catalog, defaults, inventory example |
| 2 | README standalone-first | Public readers do not need org labs to start |
| 3 | Tests | Unittest layout / hygiene / repo contracts |
| 4 | Dev deps | `requirements-dev.txt`, `.ansible-lint` |
| 5 | CI | `./tests/run_ci.sh` + `.github/workflows/ci.yml` |
| 6 | Examples / layout | `examples/secrets.example.yml` + `EXTRA_VARS_FILE` in `run.sh`; legacy entrypoints removed |

## Automated gates (run locally)

```bash
./tests/run_ci.sh
# includes: packaging smoke, unittest, syntax-check, ansible-lint, hygiene, pre-publish audit

python3 tests/check_pre_publish_audit.py
```

`check_pre_publish_audit.py` inspects the **git index** and publish candidates
(what the next commit would ship):

- no tracked live secrets / inventory (`secrets.yml`, `inventory.yml`, `hosts`, `pub_keys/`, `workspace/`)
- required publish surface present on disk (`LICENSE`, `SECURITY.md`, CI, examples, …)
- no org hostnames / `Welcomeback` / private-key markers outside allowlist (`SECURITY.md`, `docs/`, `tests/`)
- no Cyrillic in product `.yml` / `.yaml` / `.py` / `.sh` / `.cfg` (docs may stay RU)

Informational **WARN** (does not fail CI):

- `HEAD` still embeds `Welcomeback` / org fingerprints — needs commit of scrub **and** history rewrite
- required surface files present on disk but not yet staged/committed

## Manual checklist

### Working tree / next commit

- [ ] `./tests/run_ci.sh` exits 0
- [ ] `git ls-files inventory.yml hosts secrets.yml` is **empty**
- [ ] `git check-ignore -v inventory.yml` reports ignored (if local inventory present)
- [ ] Untracked publish surface is added: `LICENSE`, `SECURITY.md`, `.github/`, `requirements-dev.txt`,
      `.ansible-lint`, `examples/`, `docs/pre-publish.md`, CI helpers under `tests/`
- [ ] Product defaults use `CHANGEME` / `example.com` (no live IPs / org FQDNs / lab passwords)
- [ ] Legacy paths absent: `init-roles.yaml`, `group_vars/all/standalone.example.yml`,
      `roles/13_configure_repo/files/`

### Credentials

- [ ] Rotate any passwords / tokens that matched lab fingerprints (`Welcomeback*`, org CA / mirrors)
- [ ] Confirm no live vault / key material is tracked:
      `git ls-files | grep -E 'secrets\.yml$|\.pem$|\.key$|pub_keys/'`

### Push dry-run (no live runtime in payload)

```bash
# Index must already exclude live material:
git ls-files inventory.yml hosts secrets.yml   # empty

# What the next commit would ship (after staging publish surface):
git ls-files | head

# Optional pack of HEAD (re-run after committing scrub):
git archive --format=tar -o /tmp/atlas-node-foundation-index.tar HEAD
tar -tf /tmp/atlas-node-foundation-index.tar | grep -E 'Welcomeback|mxhash\.com' \
  && echo 'FAIL: fingerprint still in archive' || echo 'OK: no fingerprint in archive paths/content check separately'
```

Do **not** `git add inventory.yml`, `hosts`, filled secrets, or `pub_keys/`.

## History rewrite (separate, after green 0–7 tree)

Current `HEAD` / older commits still contain lab passwords and org FQDNs (for example
`Welcomeback1*` in `group_vars/all/atlas-node-foundation.yml` and `roles/00_init/defaults/main.yml`,
`ca.mxhash.com`, `*.mxhash.com` host examples). Working-tree scrub alone is **not**
enough for a public GitHub.

Choose one:

1. **`git filter-repo` / BFG** — purge blob strings (`Welcomeback`, `mxhash.com`, …) and
   obsolete paths, then force-replace remotes; or
2. **Orphan branch** — export only the cleaned tree onto a new root commit and publish that.

Document the rewrite in release notes. Re-clone after rewrite. Keep local inventory /
secrets via gitignore ([`SECURITY.md`](../SECURITY.md)).

This repository does **not** automate filter-repo (destructive; operator-owned).

## Done criteria

Public remote may be opened only when:

1. Automated gates above are green on the commit you intend to publish
2. Manual checklist items are checked
3. History rewrite (or orphan publish) is completed **or** you explicitly accept that
   historical blobs remain reachable (not recommended)

Filter-repo / orphan publish remains **out of scope** for automated CI.
