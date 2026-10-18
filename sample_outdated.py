#!/usr/bin/python3
"""Sample N packages untouched for a while and report which look outdated vs upstream.

Repology is unreachable in some environments (bulk outdated-list dead there), so this
falls back to last_update.py's per-package Anitya check, run only on a random sample
of stale-looking packages instead of the whole project.
"""
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
from datetime import datetime

from last_update import (
    ANITYA_DISTRO,
    OBSAPIURL,
    cli_tools_installed,
    convert_to_epoch,
    get_last_changes,
)

LAST_UPDATE_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_update.py")


def list_packages(osc_cmd: list[str], project: str) -> list[str]:
    out = subprocess.run(osc_cmd + ["ls", project], capture_output=True, text=True, check=True)
    return out.stdout.split()


def in_age_window(osc_cmd: list[str], project: str, package: str,
                   oldest_epoch: float, newest_epoch: float) -> bool:
    changes = get_last_changes(osc_cmd, project, package)
    if not changes:
        return False
    epoch = convert_to_epoch(" ".join(changes))
    return epoch is not None and oldest_epoch <= epoch <= newest_epoch


def iter_stale_candidates(osc_cmd: list[str], project: str, min_age_days: int, max_age_days: int):
    "yield packages last changed between min_age_days and max_age_days ago, in random order"
    packages = list_packages(osc_cmd, project)
    random.shuffle(packages)
    now = datetime.now().timestamp()
    oldest_epoch = now - max_age_days * 86400
    newest_epoch = now - min_age_days * 86400
    for i, pkg in enumerate(packages, 1):
        print(f"\rscanning {i}/{len(packages)}: {pkg}" + " " * 20,
              end="", file=sys.stderr, flush=True)
        if in_age_window(osc_cmd, project, pkg, oldest_epoch, newest_epoch):
            yield pkg


def has_pending_request(osc_cmd: list[str], project: str, package: str) -> bool:
    "true if package has an open (new/review) submit/update request, i.e. already being handled"
    out = subprocess.run(osc_cmd + ["request", "list", "-s", "new,review", project, package],
                         capture_output=True, text=True, check=True)
    return not out.stdout.startswith("No results")


def check_package(pkg: str, project: str, apiurl: str, anitya_distro: str) -> dict | None:
    result = subprocess.run(
        [sys.executable, LAST_UPDATE_PY, pkg, "-m", "-p", project,
         "--apiurl", apiurl, "--anitya-distro", anitya_distro],
        capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--project", default="openSUSE:Factory",
                         help="project to sample from [default: openSUSE:Factory]")
    parser.add_argument("--apiurl", default=OBSAPIURL)
    parser.add_argument("-n", "--count", type=int, default=20,
                         help="how many outdated packages to find [default: 20]")
    parser.add_argument("--min-age-days", type=int, default=60,
                         help="only consider packages untouched for at least this "
                              "many days [default: 60]")
    parser.add_argument("--max-age-days", type=int, default=730,
                         help="exclude packages untouched for longer than this "
                              "many days, likely abandoned [default: 730]")
    parser.add_argument("--anitya-distro", default=ANITYA_DISTRO)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not cli_tools_installed():
        print("Error: missing required tool 'osc' or 'rpmspec'.", file=sys.stderr)
        return 1

    osc_cmd = ["osc", "--apiurl", args.apiurl]
    candidates = iter_stale_candidates(osc_cmd, args.project, args.min_age_days, args.max_age_days)

    outdated = []
    for pkg in candidates:
        if len(outdated) >= args.count:
            break
        print(f"\rchecking {pkg} against upstream ({len(outdated)}/{args.count} found)" + " " * 20,
              end="", file=sys.stderr, flush=True)
        info = check_package(pkg, args.project, args.apiurl, args.anitya_distro)
        if info and info["upstream_newer"] and not has_pending_request(osc_cmd, args.project, pkg):
            outdated.append((pkg, info["version"], info["upstream_version"]))
            cols = shutil.get_terminal_size((80, 20)).columns
            print(f"\r{' ' * (cols - 1)}\r", end="", file=sys.stderr, flush=True)
            print(f"{pkg}: {info['version']} -> {info['upstream_version']}", flush=True)
            if len(outdated) >= args.count:
                break
    print(file=sys.stderr)  # end the progress line

    if not outdated:
        print("No outdated candidates found.")
        return 0

    if len(outdated) < args.count:
        print(f"\n(only found {len(outdated)}/{args.count}: ran out of packages in the "
              f"{args.min_age_days}-{args.max_age_days} day window)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
