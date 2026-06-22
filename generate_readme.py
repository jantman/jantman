#!/usr/bin/env python3
"""
Generate README.md for my GitHub profile (github.com/jantman/jantman).

Usage:
    python generate_readme.py            # regenerate README.md
    python generate_readme.py --stdout   # print to stdout instead of writing

To add/remove a project, edit the CATEGORIES data structure below: each entry
is just an "owner/repo" string. Descriptions and star counts are pulled live
from the GitHub API at generation time, so you never have to keep them in sync
by hand.

Auth: uses GITHUB_TOKEN from the environment if set, otherwise falls back to
`gh auth token`. A token is recommended to avoid the 60-req/hr unauthenticated
rate limit.
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request

# --------------------------------------------------------------------------- #
# Content you edit by hand
# --------------------------------------------------------------------------- #

INTRO = """\
### Hi, I'm Jason 👋 (a.k.a. Antman or Jantman)

Director of SRE [@manheim](https://github.com/manheim) / [@Cox-Automotive](https://github.com/Cox-Automotive).
Tooling & automation developer, F/OSS lover, maker, tinkerer, amateur machinist, and generator of half-finished
projects. Fixer-of-things and board member [@DecaturMakers](https://github.com/DecaturMakers).
"""

# Ordered list of (category title, [list of "owner/repo"]). Reorder freely.
# Guideline: keep this to actively-maintained, public, non-fork repos from
# roughly the last year or two.
CATEGORIES = [
    ("🏠 Home Automation", [
        "jantman/kodi-benq-projector-control",
        "jantman/py-vista-turbo-serial",
        "jantman/seeed-sensecap-indicator",
        "jantman/docker-zoneminder",
        "jantman/zoneminder-prometheus-exporter",
        "jantman/zoneminder-loki",
        "jantman/docker-zm-mlapi",
        "jantman/my-house",
        "jantman/house-electrical",
    ]),
    ("🔌 Hardware &amp; Embedded", [
        "jantman/ford-f150-gen14-can-bus-interface",
        "jantman/metrology-data-capture",
        "jantman/owon-xdm1041-server",
        "jantman/bk-precision-169x-server",
        "jantman/levoit-LV-PUR131-fan-controller",
        "jantman/moonlander-qmk-layout",
    ]),
    ("🛠️ Maker &amp; Fabrication", [
        "jantman/workshop-inventory-tracking",
        "jantman/machining-projects",
        "jantman/cnc-projects",
        "jantman/3d-printed-things",
        "jantman/laser-cutter-projects",
    ]),
    ("🐍 Apps &amp; Tooling", [
        "jantman/biweeklybudget",
        "jantman/misc-scripts",
        "jantman/repostatus.org",
    ]),
    ("🤖 Decatur Makers", [
        "DecaturMakers/machine-access-control",
        "DecaturMakers/equipment-status-board",
        "DecaturMakers/kiosk-show-replacement",
    ]),
    ("📡 Networking &amp; Monitoring", [
        "jantman/python-wifi-survey-heatmap",
        "jantman/unifi-mongodb-logs-to-loki",
        "jantman/prometheus-synology-api-exporter",
        "jantman/prometheus-snmp-exporter-synology-ds1621",
    ]),
    ("☁️ Cloud, DevOps &amp; Infra", [
        "jantman/grafana-cdktf-helpers",
        "jantman/raspberry-pi-imager",
        "jantman/arch-pkgbuilds",
        "jantman/puppet-shared_infra",
    ]),
]

# Layout: "list" = one bullet per repo with description (more informative)
#         "inline" = repos as dot-separated links under each category (most compact)
LAYOUT = "list"

# Show a ★ star count next to repos with at least this many stars (0 = never).
STAR_THRESHOLD = 25

OUTPUT_FILE = "README.md"

# --------------------------------------------------------------------------- #
# Generation machinery (you shouldn't need to touch below here)
# --------------------------------------------------------------------------- #


def github_token():
    import os
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    try:
        out = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def fetch_repo(full_name, token):
    """Return dict of metadata for owner/repo from the GitHub API."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{full_name}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "jantman-readme-generator",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"  ! {full_name}: HTTP {e.code} {e.reason}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"  ! {full_name}: {e.reason}", file=sys.stderr)
        return None
    return {
        "full_name": data["full_name"],
        "name": data["name"],
        "url": data["html_url"],
        "description": (data.get("description") or "").strip(),
        "stars": data.get("stargazers_count", 0),
        "archived": data.get("archived", False),
    }


def star_badge(stars):
    if STAR_THRESHOLD and stars >= STAR_THRESHOLD:
        return f" ★{stars:,}"
    return ""


def render_category_list(title, repos):
    lines = [f"#### {title}", ""]
    for r in repos:
        desc = f" — {r['description']}" if r["description"] else ""
        lines.append(f"- **[{r['name']}]({r['url']})**{desc}{star_badge(r['stars'])}")
    lines.append("")
    return lines


def render_category_inline(title, repos):
    links = " · ".join(
        f"[{r['name']}]({r['url']}){star_badge(r['stars'])}" for r in repos
    )
    return [f"**{title}** — {links}", ""]


def render(categories_data):
    out = [INTRO.rstrip(), "", "---", ""]
    renderer = render_category_inline if LAYOUT == "inline" else render_category_list
    for title, repos in categories_data:
        if repos:
            out.extend(renderer(title, repos))
    out.append("<sub><i>This page is generated by "
               "<a href=\"generate_readme.py\">generate_readme.py</a>.</i></sub>")
    out.append("")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdout", action="store_true",
                        help="print to stdout instead of writing README.md")
    args = parser.parse_args()

    token = github_token()
    if not token:
        print("Warning: no GitHub token found (set GITHUB_TOKEN or run "
              "`gh auth login`); subject to a 60-req/hr rate limit.",
              file=sys.stderr)

    categories_data = []
    for title, repo_names in CATEGORIES:
        print(f"Fetching {title} ...", file=sys.stderr)
        repos = []
        for full_name in repo_names:
            meta = fetch_repo(full_name, token)
            if meta is None:
                continue
            if meta["archived"]:
                print(f"  · skipping archived {full_name}", file=sys.stderr)
                continue
            repos.append(meta)
        categories_data.append((title, repos))

    content = render(categories_data)

    if args.stdout:
        sys.stdout.write(content)
    else:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Wrote {OUTPUT_FILE} ({content.count(chr(10)) + 1} lines).",
              file=sys.stderr)


if __name__ == "__main__":
    main()
