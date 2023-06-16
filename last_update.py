#!/usr/bin/python3
import subprocess
import argparse
import re
from datetime import datetime
import requests

from cmp_version import VersionString


# TODO make these configurable via cli
APIURL = "https://api.opensuse.org"
MAINPROJECT = "openSUSE:Factory"
# 

OSC_CMD = ['osc', '--apiurl', APIURL]

REPOLOGY_APIURL = 'https://repology.org/api/v1/project/'


def exec_process(cmdline: list[str]):
    "helper to execute external process"
    return subprocess.Popen(
        cmdline, stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, encoding='utf8')


def convert_to_epoch(timestamp):
    "given a date string, returns time in epoch (seconds from 1/1/1970)"
    try:
        # Attempt to parse timestamp in the format 'Month Day Hour:Minute'
        timestamp_with_year = f'{timestamp} {datetime.now().year}'

        # Attempt to parse timestamp in the format 'Month Day Hour:Minute Year'
        date_obj = datetime.strptime(timestamp_with_year, '%b %d %H:%M %Y')

    except ValueError:
        try:
            # Attempt to parse timestamp in the format 'Month Day Year'
            date_obj = datetime.strptime(timestamp, '%b %d %Y')
        except ValueError:
            return None

    epoch_time = int(date_obj.timestamp())
    return epoch_time


def get_last_changes(package: str):
    "parse project to get last changes modification date"
    try:
        proc = exec_process(
            OSC_CMD+["ls", "-l", f"{MAINPROJECT}/{package}"])
        for line in proc.stdout.readlines():
            if f"{package}.changes" not in line:
                continue
            return line.split()[3:6]
    except Exception():
        return []


def is_numeric(version: str) -> bool:
    "return true if given version is numeric"
    return re.search(r"^\d+", version) is not None


def get_obs_version(package: str) -> str:
    "query spec file in obs for the package version"
    try:
        osc = exec_process(
            OSC_CMD+["cat", f"{MAINPROJECT}/{package}/{package}.spec"]
        )
        rpmspec = subprocess.check_output(
            ('rpmspec', '-q', '/dev/stdin', '--queryformat=%{VERSION} '),
            stdin=osc.stdout,  stderr=subprocess.DEVNULL, encoding='utf8')
        osc.wait()
        version = str(rpmspec).split()[0]
        if is_numeric(version):
            return version
        return "_VERSION_"

    except Exception as exc:
        print(f"Error in getting version from OBS: {exc}")
        return ""


def filter_repo(items: list[dict], refversion: str) -> list[dict]:
    """uses some heuristic to create a list of only entries with a newer version
       on any parsing issue, returns the original list"""
    try:
        refv = VersionString(refversion)
        return list(filter(lambda x: refv < VersionString(x['version']), items))
    except ValueError:
        return items


def is_newer_on_repology(package: str, refversion: str) -> int:
    "query repology.org API to get same named packaged with newer version"
    try:
        response = requests.get(f"{REPOLOGY_APIURL}/{package}",timeout=30)
        results = [r for r in response.json() if r['status'] ==
                   'newest' and r['version'] != refversion]
        # if the version is numeric, try to compare and filter out the one lesser
        if is_numeric(refversion):
            results = filter_repo(results, refversion)
        return len(results)
    except requests.exceptions.RequestException:
        return """Sorry, we could not establish a connection to repology.org.
        Please make sure that you are connected to the internet and try again"""


def main():
    "program entry point"
    parser = argparse.ArgumentParser(
        prog='last update',
        description='tells you when a package was last updated',
    )
    parser.add_argument(
        'package', help='the package name to check (ex bash, vim ...)')
    parser.add_argument(
        '-m', '--machine', help='Use machine processable output instead of human readable', 
        action='store_true')
    args = parser.parse_args()
    output_str = f"- {args.package} "
    changes = get_last_changes(args.package)
    if not changes:
        output_str += "Error in getting information. Does this package exist in Factory ?"
        return output_str
    else:
        obs_version = get_obs_version(args.package)
        changes = ' '.join(changes)
        if args.machine:
            changes = convert_to_epoch(changes)
        output_str += f"on {MAINPROJECT} is {obs_version} changed on {changes}"

    repo_with_new_packages = is_newer_on_repology(args.package, obs_version)
    if is_numeric(obs_version) and repo_with_new_packages:
        if args.machine:
            output_str += " "
        else:
            output_str += "\n"
        output_str += f"Other {repo_with_new_packages} repos may have newer versions"
    return output_str


# when imported as module, do not run
if __name__ == '__main__':
    print(main())
