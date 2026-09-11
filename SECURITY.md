# Security

## Reporting

If you discover a security issue in this repository, please open a private report with the
maintainers (do not file a public issue with exploit details or credentials).

## Secrets in this repo

Do **not** commit:

- host bootstrap passwords (`initial_password`, root / system user passwords)
- SSH private keys or agent identities
- deprecated monolithic `secrets.yml` / `*.vault` with live values
- live inventory with production hosts (`inventory.yml`, local `hosts`)
- site CA / mirror credentials or internal package-repo tokens
- controller runtime under `workspace/` / `.ansible/`

Prefer `group_vars/all/atlas-node-foundation.secrets.yml` with Ansible Vault (trackable; do **not** gitignore). Standalone operators may also use `EXTRA_VARS_FILE` / `examples/secrets.example.yml` **outside** the tree. A monolithic `secrets.yml` is deprecated and must not hold live credentials in git.

Prefer SSH keys (`init_ssh_connect: key`) and external secret stores in production.

Tracked examples must stay inert (`CHANGEME`, `example.com`). Do not re-introduce lab passwords
or org FQDNs into product paths.

Copy `examples/secrets.example.yml` outside the repo and pass it with
`EXTRA_VARS_FILE=/path/to/atlas-node-foundation.secrets.yml ./run.sh` — never commit filled copies.

## Local runtime (gitignored)

The following stay on the operator workstation and must not be pushed:

- `inventory.yml`, `hosts`
- live `atlas-node-foundation.secrets.yml` plaintext (prefer Vault) / deprecated `secrets.yml`
- `pub_keys/` (local authorized_keys material)
- `workspace/`, `.ansible/`, `.ansible_facts_cache/`
- host overrides under `host_vars/` except tracked `example.yml` / `*.example.yml`

## Git history note (pre-publish)

Older commits (still reachable from `HEAD` until rewritten) embedded org lab fingerprints in
defaults and examples, including:

- bootstrap passwords matching `Welcomeback*`
  (`group_vars/all/atlas-node-foundation.yml`, `roles/00_init/defaults/main.yml`)
- org CA URL `https://ca.mxhash.com:8443/roots.pem`
  (`group_vars/all/atlas-node-foundation.yml`, `roles/11_certificates/defaults/main.yml`)
- example hostnames under `*.mxhash.com` (`host_vars/example.yml`)

The working tree is scrubbed toward `CHANGEME` / `example.com`. Historical blobs remain
reachable until history is rewritten.

## Guardrails (publish track)

- `.gitignore` excludes live `inventory.yml`, `hosts`, `secrets.yml`, `pub_keys/`, `workspace/`
- `./tests/run_ci.sh` + `.github/workflows/ci.yml` run unittest, syntax-check, ansible-lint,
  fingerprint hygiene, and `tests/check_pre_publish_audit.py`
- Do not re-add live inventories, vault files, or org lab passwords to tracked paths

Full pre-publish checklist (push dry-run, credential rotation, history rewrite):
[`docs/pre-publish.md`](docs/pre-publish.md).

Before making this repository public:

1. Confirm no live secrets remain in **tracked** files; rotate anything that may have been pushed.
2. Confirm `git ls-files inventory.yml hosts secrets.yml` is empty before push.
3. Follow [`docs/pre-publish.md`](docs/pre-publish.md) — including history rewrite
   (`git filter-repo` / BFG) or an orphan cleaned branch.
4. Assume historical blobs remain reachable until remotes are rewritten / force-replaced.
