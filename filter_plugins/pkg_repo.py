"""Package-repo helpers for atlas-node-foundation (Phase 2+).

Client write path uses leaf ``pkg_repos[].uri`` verbatim — no mode resolver.
``pkg_repo_resolve`` maps catalog ``name`` → content metadata for templates.
``pkg_repo_nginx_uri`` is an optional inventory/helper for baking nginx URIs.
``pkg_repo_enrich`` attaches metadata + applicability for the current host.
"""

from __future__ import annotations

import re

_APT_DEBIAN = ("Debian",)
_APT_UBUNTU = ("Ubuntu",)
_APT_BOTH = ("Debian", "Ubuntu")
_YUM_OL = ("OracleLinux",)

_STATIC = {
    "debian-main": {
        "family": "apt",
        "kind": "debian-main",
        "distributions": list(_APT_DEBIAN),
        "needs_keyring": None,
        "ol_major": None,
    },
    "debian-security": {
        "family": "apt",
        "kind": "debian-security",
        "distributions": list(_APT_DEBIAN),
        "needs_keyring": None,
        "ol_major": None,
    },
    "debian-non-free": {
        "family": "apt",
        "kind": "debian-non-free",
        "distributions": list(_APT_DEBIAN),
        "needs_keyring": None,
        "ol_major": None,
    },
    "ubuntu": {
        "family": "apt",
        "kind": "ubuntu",
        "distributions": list(_APT_UBUNTU),
        "needs_keyring": None,
        "ol_major": None,
    },
    "debian-containerd": {
        "family": "apt",
        "kind": "docker-deb",
        "distributions": list(_APT_DEBIAN),
        "needs_keyring": "docker",
        "ol_major": None,
    },
    "ubuntu-containerd": {
        "family": "apt",
        "kind": "docker-deb",
        "distributions": list(_APT_UBUNTU),
        "needs_keyring": "docker",
        "ol_major": None,
    },
    "pgdg-apt": {
        "family": "apt",
        "kind": "pgdg-apt",
        "distributions": list(_APT_BOTH),
        "needs_keyring": "pgdg",
        "ol_major": None,
    },
    "pgdg-yum": {
        "family": "yum",
        "kind": "pgdg-yum",
        "distributions": list(_YUM_OL),
        "needs_keyring": None,
        "ol_major": None,
        "baseurl_suffix": "pgdg",
    },
    "yum_docker-ce-stable-9": {
        "family": "yum",
        "kind": "yum-generic",
        "distributions": list(_YUM_OL),
        "needs_keyring": None,
        "ol_major": 9,
    },
    "yum_docker-ce-stable-10": {
        "family": "yum",
        "kind": "yum-generic",
        "distributions": list(_YUM_OL),
        "needs_keyring": None,
        "ol_major": 10,
    },
}

for _name in (
    "OL9_baseos",
    "OL9_appstream",
    "OL9_addons",
    "OL9_developer",
    "OL9_developer_EPEL",
    "OL9_codeready_builder",
    "OL9_kvm",
    "OL9_MODRHCK",
    "OL9_oraclelinuxmanager210",
    "OL9_RDMA",
    "OL9_UEKR7",
    "OL9_UEKR8",
):
    _STATIC[_name] = {
        "family": "yum",
        "kind": "yum-generic",
        "distributions": list(_YUM_OL),
        "needs_keyring": None,
        "ol_major": 9,
    }

for _name in (
    "OL10_baseos",
    "OL10_appstream",
    "OL10_addons",
    "OL10_developer",
    "OL10_developer_EPEL",
    "OL10_RDMA",
    "OL10_UEKR8",
    "OL10_builder",
):
    _STATIC[_name] = {
        "family": "yum",
        "kind": "yum-generic",
        "distributions": list(_YUM_OL),
        "needs_keyring": None,
        "ol_major": 10,
    }

_K8S_APT = re.compile(r"^k8s-ubuntu-(\d+\.\d+)$")
_K8S_YUM = re.compile(r"^k8s-(\d+\.\d+)$")


def _slug_host(value):
    slug = re.sub(r"[^a-zA-Z0-9._-]", "-", value or "")
    return slug.replace(".", "-")


def pkg_repo_resolve(name):
    """Return content metadata for a catalog name, or None if unknown."""
    if not name:
        return None
    if name in _STATIC:
        return dict(_STATIC[name])
    if _K8S_APT.match(name):
        return {
            "family": "apt",
            "kind": "k8s-deb",
            "distributions": list(_APT_BOTH),
            "needs_keyring": "k8s",
            "ol_major": None,
        }
    if _K8S_YUM.match(name):
        return {
            "family": "yum",
            "kind": "yum-generic",
            "distributions": list(_YUM_OL),
            "needs_keyring": None,
            "ol_major": None,
        }
    return None


def pkg_repo_nginx_uri(name, nginx_domain):
    """Bake a nginx pkg-repo mirror URI for inventory/templates."""
    domain = (nginx_domain or "").strip()
    if not domain or not name:
        return ""
    return "https://{}.{}".format(_slug_host(name), domain)


def pkg_repo_applies(meta, distribution, distribution_major_version=None):
    """Whether this repo content should be written on the current host."""
    if not meta:
        return False
    dists = meta.get("distributions") or []
    if distribution not in dists:
        return False
    ol_major = meta.get("ol_major")
    if ol_major is None:
        return True
    try:
        major = int(str(distribution_major_version).split(".")[0])
    except (TypeError, ValueError):
        return False
    return major == int(ol_major)


def pkg_repo_enrich(pkg_repos, distribution, distribution_major_version=None):
    """Attach ``_meta`` / ``_applies`` and normalize enabled/uri for each entry."""
    out = []
    for item in pkg_repos or []:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or ""
        meta = pkg_repo_resolve(name)
        uri = (item.get("uri") or "").rstrip("/")
        enabled = item.get("enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.lower() in ("1", "true", "yes")
        else:
            enabled = bool(enabled)
        out.append(
            {
                "name": name,
                "enabled": enabled,
                "uri": uri,
                "_meta": meta,
                "_applies": pkg_repo_applies(
                    meta, distribution, distribution_major_version
                ),
            }
        )
    return out


def pkg_repo_by_family(repos, family):
    """Filter enriched repos by ``_meta.family`` (apt|yum)."""
    out = []
    for item in repos or []:
        meta = (item or {}).get("_meta") or {}
        if meta.get("family") == family:
            out.append(item)
    return out


def pkg_repo_needs_keyring(repos, keyring):
    """True if any enriched active-style repo needs the given keyring id."""
    for item in repos or []:
        meta = (item or {}).get("_meta") or {}
        if meta.get("needs_keyring") == keyring:
            return True
    return False


class FilterModule(object):
    def filters(self):
        return {
            "pkg_repo_resolve": pkg_repo_resolve,
            "pkg_repo_nginx_uri": pkg_repo_nginx_uri,
            "pkg_repo_applies": pkg_repo_applies,
            "pkg_repo_enrich": pkg_repo_enrich,
            "pkg_repo_by_family": pkg_repo_by_family,
            "pkg_repo_needs_keyring": pkg_repo_needs_keyring,
        }
