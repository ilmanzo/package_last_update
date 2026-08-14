#!/usr/bin/python3
"""Report when an openSUSE OBS package last changed and whether newer versions
exist elsewhere (queried via repology.org)."""
import sys
import json
import subprocess
import argparse
import re
from datetime import datetime
from shutil import which
from tempfile import NamedTemporaryFile

import requests
import packaging.version

__version__ = "1.1.0"

# default OBS instance API URL
OBSAPIURL = "https://api.opensuse.org"
REPOLOGY_APIURL = "https://repology.org/api/v1/project/"
ANITYA_APIURL = "https://release-monitoring.org/api/v2/packages/"
ANITYA_DISTRO = "openSUSE"

# non-browser UA: repology's bulk policy needs it, and it slips past Anitya's Anubis bot check
USER_AGENT = "package_last_update https://github.com/ilmanzo/package_last_update"

# exit codes
EXIT_OK = 0
EXIT_MISSING_TOOLS = 1
EXIT_NOT_FOUND = 2
EXIT_NETWORK = 3


def convert_to_epoch(timestamp: str, now: datetime | None = None) -> int | None:
    "given a date string like 'Dec 07 2022' or 'Jan 03 10:44', return unix epoch"
    now = now or datetime.now()
    try:
        # recent changes have no year; osc prints 'Mon Day HH:MM' instead
        date_obj = datetime.strptime(f"{timestamp} {now.year}", "%b %d %H:%M %Y")
        # a change can only be in the past: a future date means it was last year
        if date_obj > now:
            date_obj = date_obj.replace(year=date_obj.year - 1)
    except ValueError:
        try:
            date_obj = datetime.strptime(timestamp, "%b %d %Y")
        except ValueError:
            return None
    return int(date_obj.timestamp())


def is_numeric(version: str) -> bool:
    "return true if given version starts with a digit"
    return re.match(r"\d+", version) is not None


def get_last_changes(osc_cmd: list[str], mainproject: str, package: str) -> list[str]:
    "parse `osc ls -l` output to get the last-changed date of <package>.changes"
    try:
        proc = subprocess.run(
            osc_cmd + ["ls", "-l", f"{mainproject}/{package}"],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    for line in proc.stdout.splitlines():
        if f"{package}.changes" in line:
            return line.split()[3:6]
    return []


def get_obs_version(osc_cmd: list[str], mainproject: str, package: str) -> str:
    "fetch the package .spec from OBS and extract its version via rpmspec"
    spec = package + ".spec"
    try:
        cat = subprocess.run(
            osc_cmd + ["cat", mainproject, package, spec],
            capture_output=True, text=True, timeout=30, check=True,
        )
        # rpmspec needs a real file; write the fetched spec to a temp one.
        # ponytail: OBS specs are semi-trusted — rpmspec evaluates %() shell
        # macros at parse time, so this runs whatever the spec's author put there.
        with NamedTemporaryFile("w", suffix=".spec") as tmp:
            tmp.write(cat.stdout)
            tmp.flush()
            rpmspec = subprocess.check_output(
                ("rpmspec", "-q", tmp.name, "--queryformat=%{VERSION} "),
                stderr=subprocess.DEVNULL, text=True,
            )
        version = rpmspec.split()[0]
        return version if is_numeric(version) else "_VERSION_"
    except (subprocess.SubprocessError, OSError, IndexError) as exc:
        print(f"Error getting version from OBS: {exc}", file=sys.stderr)
        return ""


def _parse_version(version: str) -> packaging.version.Version:
    "parse a version, treating anything unparseable as the lowest possible"
    try:
        return packaging.version.parse(version)
    except packaging.version.InvalidVersion:
        return packaging.version.parse("0")


def filter_repo(items: list[dict], refversion: str) -> list[dict]:
    """keep only entries whose version is newer than refversion;
       on any parsing issue, return the original list"""
    try:
        refv = packaging.version.parse(refversion)
        return [x for x in items if refv < packaging.version.parse(x["version"])]
    except packaging.version.InvalidVersion:
        return items


def is_newer_on_repology(package: str, refversion: str) -> tuple[int, str | None]:
    """query repology.org for same-named packages that are newer.
       returns (count, highest_newer_version) or (-1, None) on connection error."""
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        response = session.get(f"{REPOLOGY_APIURL}{package}", timeout=30)
        response.raise_for_status()
        results = [r for r in response.json()
                   if r["status"] == "newest" and r["version"] != refversion]
        # only try to compare/filter when the reference version is numeric
        if is_numeric(refversion):
            results = filter_repo(results, refversion)
    except requests.exceptions.RequestException as e:
        print("Error:", repr(e), file=sys.stderr)
        return -1, None
    if not results:
        return 0, None
    newest = max((r["version"] for r in results), key=_parse_version)
    return len(results), newest


def anitya_upstream(package: str, distro: str = ANITYA_DISTRO) -> str | None:
    """latest upstream version from release-monitoring.org (Anitya) for the given
       distro package, or None if it isn't tracked or the service is unreachable.
       Secondary source: failures warn but don't abort the run."""
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        response = session.get(
            ANITYA_APIURL, params={"distribution": distro, "name": package}, timeout=30)
        response.raise_for_status()
        items = response.json().get("items", [])
    except requests.exceptions.RequestException as e:
        print("Warning: release-monitoring.org lookup failed:", repr(e), file=sys.stderr)
        return None
    if not items:
        return None
    return items[0].get("stable_version") or items[0].get("version") or None


def cli_tools_installed() -> bool:
    "return true if both required external tools are on $PATH"
    return all(which(tool) is not None for tool in ("osc", "rpmspec"))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="last_update.py",
        description="tells you when a package was last updated",
    )
    parser.add_argument("package",
                        help="the package name to check (ex bash, vim ...)")
    parser.add_argument("-m", "--machine", action="store_true",
                        help="emit machine-readable JSON instead of human text")
    parser.add_argument("-p", "--project", default="openSUSE:Factory",
                        help="root/base project to look in [default: openSUSE:Factory]")
    parser.add_argument("--apiurl", default=OBSAPIURL,
                        help=f"the OBS instance to query [default: {OBSAPIURL}]")
    parser.add_argument("--anitya-distro", default=ANITYA_DISTRO,
                        help="distribution name for the release-monitoring.org lookup "
                             f"[default: {ANITYA_DISTRO}]")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    "core logic; prints output, returns process exit code"
    if not cli_tools_installed():
        print("Error: missing required tool 'osc' or 'rpmspec'. "
              "Install them and ensure they are in $PATH.", file=sys.stderr)
        return EXIT_MISSING_TOOLS

    osc_cmd = ["osc", "--apiurl", args.apiurl]
    changes = get_last_changes(osc_cmd, args.project, args.package)
    if not changes:
        print(f"Error: could not find '{args.package}' in {args.project}.",
              file=sys.stderr)
        return EXIT_NOT_FOUND

    obs_version = get_obs_version(osc_cmd, args.project, args.package)
    changes_str = " ".join(changes)
    count, newest = is_newer_on_repology(args.package, obs_version)
    if count < 0:
        print("Error: could not reach repology.org. "
              "Check your connection and retry.", file=sys.stderr)
        return EXIT_NETWORK

    has_newer = is_numeric(obs_version) and count > 0

    upstream = anitya_upstream(args.package, args.anitya_distro)
    upstream_comparable = bool(upstream and is_numeric(obs_version) and is_numeric(upstream))
    upstream_newer = upstream_comparable and _parse_version(obs_version) < _parse_version(upstream)
    upstream_current = upstream_comparable and not upstream_newer

    if args.machine:
        print(json.dumps({
            "package": args.package,
            "project": args.project,
            "version": obs_version,
            "changed": changes_str,
            "changed_epoch": convert_to_epoch(changes_str),
            "newer_repos": count if has_newer else 0,
            "newest_version": newest if has_newer else None,
            "upstream_version": upstream,
            "upstream_newer": upstream_newer,
        }))
    else:
        line = f"- {args.package} on {args.project} is {obs_version} changed on {changes_str}"
        # up-to-date is the quiet case: keep it inline, no extra line
        if upstream_current:
            line += " (up to date with upstream)"
        if has_newer:
            line += f"\n  Other {count} repos may have newer versions"
            if newest:
                line += f" (newest: {newest})"
            line += ", consider updating!"
        if upstream_newer:
            line += f"\n  release-monitoring.org: upstream {upstream} (newer!)"
        print(line)
    return EXIT_OK


# when imported as module, do not run
if __name__ == "__main__":
    sys.exit(run(parse_args()))
