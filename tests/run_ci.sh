#!/usr/bin/env bash
# Local parity with .github/workflows/ci.yml
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== packaging / layout smoke =="
test -f LICENSE
test -f SECURITY.md
test -f README.md
test -f run.sh
test -x run.sh
test -x tests/run_ci.sh
test -f tests/check_pre_publish_audit.py
test -f docs/pre-publish.md
test -f docs/pkg-repos-contract.md
test -f docs/pkg-repos-catalog.md
test -f docs/pkg-repos-catalog.yml
test -f CHANGELOG.md
test -f inventory-example.yml
test -f group_vars/all/atlas-node-foundation.yml
test -f group_vars/all/atlas-node-foundation.secrets.yml
test -f playbooks/init_nodes.yaml
test -f requirements.yml
test -f requirements-dev.txt
test -f .ansible-lint
test -f .github/workflows/ci.yml
test -f examples/secrets.example.yml
echo "OK: packaging layout"

echo "== unittest =="
python3 -m unittest discover -s tests -v

echo "== ansible syntax-check =="
ansible-playbook --syntax-check -i inventory-example.yml playbooks/init_nodes.yaml

echo "== ansible-lint (profile min) =="
ansible-lint --profile min

echo "== publish hygiene smoke =="
# Secret / password fingerprints (SECURITY.md may document historical ones — excluded).
if grep -RIn --exclude-dir=.git --exclude-dir=workspace --exclude-dir=__pycache__ \
  --exclude=SECURITY.md --exclude='*test*.py' \
  -e 'Welcomeback' -e 'BEGIN OPENSSH PRIVATE' -e 'BEGIN RSA PRIVATE' \
  -- roles playbooks group_vars host_vars examples filter_plugins inventory-example.yml run.sh ansible.cfg requirements.yml; then
  echo "possible secret material in tracked sources" >&2
  exit 1
fi
# Org hostname fingerprint (allow in SECURITY.md / tests only).
if grep -RIn --exclude-dir=.git --exclude-dir=workspace --exclude-dir=__pycache__ \
  --exclude=SECURITY.md --exclude='*test*.py' \
  -e 'mxhash' \
  -- roles playbooks group_vars host_vars examples filter_plugins inventory-example.yml run.sh ansible.cfg requirements.yml README.md; then
  echo "org fingerprint mxhash found outside docs/tests" >&2
  exit 1
fi

echo "== pre-publish audit (git index + candidates) =="
python3 tests/check_pre_publish_audit.py

echo "CI checks passed."
