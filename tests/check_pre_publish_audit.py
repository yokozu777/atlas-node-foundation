#!/usr/bin/env python3
"""Pre-publish audit against the git index (what the next commit would ship).

Gates (exit 1 on failure):
  - no tracked live inventory / secrets / runtime dirs
  - required publish surface present on disk
  - no org fingerprints / Welcomeback / private-key markers outside allowlist
  - no Cyrillic in product .yml/.yaml/.py/.sh/.cfg (docs/tests OK)

Informational WARN (does not fail):
  - HEAD tree still embeds Welcomeback / mxhash fingerprints
  - required surface files on disk but not yet in the git index
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FINGERPRINT_RE = re.compile(
    r"(?:gitea|harbor|upload|nexus|ca)\.mxhash\.com|"
    r"(?<![A-Za-z0-9_-])mxhash\.com|"
    r"/var/lib/mxhash|"
    r"[Ww]elcomeback|"
    r"ChangeMe123|"
    r"BEGIN (?:OPENSSH |RSA )?PRIVATE KEY|"
    r"\bAKIA[0-9A-Z]{16}\b",
    re.IGNORECASE,
)

ALLOWLIST_RE = re.compile(
    r"^(?:SECURITY\.md|CHANGELOG\.md|docs/|tests/"
    r"|push-gitea\.sh|push-github\.sh|git-publish-lib\.sh)"
)

CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
CYRILLIC_SCAN_SUFFIXES = {".yml", ".yaml", ".py", ".sh", ".cfg"}
CYRILLIC_ALLOW_PREFIXES = ("docs/", "tests/")

SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".woff",
    ".woff2",
    ".ttf",
    ".pyc",
}

REQUIRED_SURFACE = (
    "LICENSE",
    "SECURITY.md",
    "README.md",
    "docs/pre-publish.md",
    ".github/workflows/ci.yml",
    "tests/run_ci.sh",
    "tests/check_pre_publish_audit.py",
    "requirements.yml",
    "requirements-dev.txt",
    ".ansible-lint",
    "inventory-example.yml",
    "group_vars/all/atlas-node-foundation.yml",
    "playbooks/init_nodes.yaml",
    "run.sh",
    "examples/secrets.example.yml",
)

LEGACY_MUST_ABSENT = (
    "init-roles.yaml",
    "group_vars/all/standalone.example.yml",
)


def _git_output(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _indexed_files() -> list[str]:
    return [line for line in _git_output("ls-files").splitlines() if line.strip()]


def _publish_candidate_files() -> list[str]:
    """Indexed paths plus non-ignored untracked files (next-commit candidates)."""
    indexed = _indexed_files()
    other = [
        line
        for line in _git_output("ls-files", "--others", "--exclude-standard").splitlines()
        if line.strip()
    ]
    return sorted(set(indexed) | set(other))


def _is_allowlisted(rel: str) -> bool:
    return bool(ALLOWLIST_RE.match(rel))


def _is_risky_secret_path(rel: str) -> bool:
    name = Path(rel).name
    if name in ("secrets.yml", "secrets.yaml"):
        return True
    if rel in {"inventory.yml", "hosts", "vars-file.yml"}:
        return True
    if rel.startswith(("pub_keys/", "workspace/", ".ansible/")):
        return True
    if rel.endswith((".pem", ".key")) and "example" not in Path(rel).name.lower():
        return True
    return False


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    indexed = _indexed_files()
    indexed_set = set(indexed)
    candidates = _publish_candidate_files()

    # --- live secrets / inventory must not be in the index ---
    risky = sorted(rel for rel in indexed if _is_risky_secret_path(rel))
    if risky:
        errors.append("live secrets / inventory / runtime paths still in git index:")
        errors.extend(f"  - {rel}" for rel in risky[:40])
        if len(risky) > 40:
            errors.append(f"  - … +{len(risky) - 40} more")

    # --- legacy entrypoints must stay gone from disk and index ---
    for rel in LEGACY_MUST_ABSENT:
        on_disk = (ROOT / rel).exists()
        in_index = rel in indexed_set
        if on_disk or in_index:
            where = []
            if on_disk:
                where.append("on disk")
            if in_index:
                where.append("in git index — stage `git rm`")
            errors.append(f"legacy entrypoint still present ({', '.join(where)}): {rel}")
    files_dir = ROOT / "roles" / "13_configure_repo" / "files"
    if files_dir.exists():
        errors.append("legacy path still present on disk: roles/13_configure_repo/files/")
    indexed_files_hits = [
        rel for rel in indexed if rel.startswith("roles/13_configure_repo/files/")
    ]
    if indexed_files_hits:
        errors.append(
            "legacy roles/13_configure_repo/files/* still in git index — stage `git rm`"
        )
        errors.extend(f"  - {rel}" for rel in indexed_files_hits[:12])

    # --- required publish surface on disk ---
    for rel in REQUIRED_SURFACE:
        if not (ROOT / rel).is_file():
            errors.append(f"missing required publish file: {rel}")
        elif rel not in indexed_set:
            warnings.append(f"publish surface not yet in git index (stage before push): {rel}")

    # --- fingerprint scan on publish candidates ---
    fp_hits: list[str] = []
    for rel in candidates:
        if _is_allowlisted(rel):
            continue
        path = ROOT / rel
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if FINGERPRINT_RE.search(line):
                fp_hits.append(f"{rel}:{lineno}:{line.strip()[:160]}")
    if fp_hits:
        errors.append("org fingerprint / secret markers in publish candidate paths:")
        errors.extend(f"  - {h}" for h in fp_hits[:40])
        if len(fp_hits) > 40:
            errors.append(f"  - … +{len(fp_hits) - 40} more")

    # --- Cyrillic in product sources ---
    cyr_hits: list[str] = []
    for rel in candidates:
        if any(rel.startswith(p) for p in CYRILLIC_ALLOW_PREFIXES):
            continue
        path = ROOT / rel
        if path.suffix.lower() not in CYRILLIC_SCAN_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if CYRILLIC_RE.search(line):
                cyr_hits.append(f"{rel}:{lineno}:{line.strip()[:120]}")
    if cyr_hits:
        errors.append(
            "Cyrillic found in product .yml/.yaml/.py/.sh/.cfg "
            "(RU docs under docs/ are OK):"
        )
        errors.extend(f"  - {h}" for h in cyr_hits[:40])
        if len(cyr_hits) > 40:
            errors.append(f"  - … +{len(cyr_hits) - 40} more")

    # --- WARN: HEAD still embeds lab fingerprints ---
    for needle, label in (
        ("Welcomeback", "Welcomeback"),
        ("mxhash.com", "mxhash.com"),
    ):
        try:
            hist = subprocess.run(
                ["git", "grep", "-I", "-n", needle, "HEAD"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            if hist.returncode == 0 and hist.stdout.strip():
                warnings.append(
                    f"{label} still reachable from HEAD tree — rotate credentials and "
                    "rewrite history before public GitHub (see docs/pre-publish.md); "
                    "working-tree scrub alone is not enough"
                )
        except OSError:
            pass

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)

    if errors:
        print("\n".join(errors), file=sys.stderr)
        print("FAIL: pre-publish audit", file=sys.stderr)
        return 1

    print(
        "OK: pre-publish audit "
        f"(indexed={len(indexed)} candidates={len(candidates)}, "
        f"risky=0, fingerprint/cyrillic clean; warnings={len(warnings)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
