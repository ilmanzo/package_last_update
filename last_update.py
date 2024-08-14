#!/usr/bin/python3
import subprocess
import argparse
import re
from datetime import datetime
from shutil import which
from tempfile import TemporaryDirectory
from os import chdir
import requests

import packaging
import packaging.version


# TODO make these configurable via cli
APIURL = "https://api.opensuse.org"

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


def get_last_changes(mainproject: str, package: str):
    "parse project to get last changes modification date"
    try:
        proc = exec_process(
            OSC_CMD+["ls", "-l", f"{mainproject}/{package}"])
        for line in proc.stdout.readlines():
            if f"{package}.changes" not in line:
                continue
            return line.split()[3:6]
    except Exception():
        return []


def is_numeric(version: str) -> bool:
    "return true if given version is numeric"
    return re.search(r"^\d+", version) is not None


def get_obs_version(mainproject: str, package: str) -> str:
    "query spec file in obs for the package version"
    spec = package+'.spec'
    try:
        with TemporaryDirectory() as tmpdir:
            chdir(tmpdir)
            subprocess.run(
                OSC_CMD+["co", mainproject, package, spec],
                check=True, timeout=30
            )
            rpmspec = subprocess.check_output(
                ('rpmspec', '-q', spec, '--queryformat=%{VERSION} '),
                stderr=subprocess.DEVNULL, encoding='utf8')
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
        refv = packaging.version.parse(refversion)
        return list(filter(lambda x: refv < packaging.version.parse(x['version']), items))
    except ValueError:
        return items


def is_newer_on_repology(package: str, refversion: str) -> int:
    "query repology.org API to get same named packaged with newer version"
    try:
        session = requests.Session()
        # temp fake user agent until we figure out the rules needed for bulk API requests
        # myua = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'}
        myua = {'User-Agent': 'package_last_update https://github.com/ilmanzo/package_last_update'}
        session.headers.update(myua)
        response = session.get(f"{REPOLOGY_APIURL}{package}", timeout=30)
        results = [r for r in response.json() if r['status'] ==
                   'newest' and r['version'] != refversion]
        # if the version is numeric, try to compare and filter out the one lesser
        if is_numeric(refversion):
            results = filter_repo(results, refversion)
        return len(results)
    except requests.exceptions.RequestException as e:
        print("Error:", repr(e))
        return -1 


def cli_tools_installed():
    "uses shutil.which to check if the program is in path"
    for tool in ('osc', 'rpmspec'):
        path = which(tool)
        if path is None:
            return False
    return True


def main() -> str:
    "program entry point"
    parser = argparse.ArgumentParser(
        prog='last_update.py',
        description='tells you when a package was last updated',
    )
    parser.add_argument('package',
                        help='the package name to check (ex bash, vim ...)')
    parser.add_argument('-m', '--machine',
                        help='Use machine processable output instead of human readable',
                        action='store_true')
    parser.add_argument('-p', '--project',
                        help="The root/base project where to find the package, [default=openSUSE:Factory]",
                        default="openSUSE:Factory")
    args = parser.parse_args()
    mainproject = args.project
    output_str = f"- {args.package} "
    if not cli_tools_installed():
        return "Error, missing one of required tools: 'osc / rpmspec'. Please install and be sure to have in $PATH"
    changes = get_last_changes(mainproject, args.package)
    if not changes:
        output_str += f"Error in getting information. Does this package exist in {mainproject} ?"
        return output_str
    else:
        obs_version = get_obs_version(mainproject, args.package)
        changes = ' '.join(changes)
        if args.machine:
            changes = convert_to_epoch(changes)
        output_str += f"on {mainproject} is {obs_version} changed on {changes}"

    repo_with_new_packages = is_newer_on_repology(args.package, obs_version)
    if repo_with_new_packages < 0:
        return """Sorry, we could not establish a connection to repology.org.
        Please make sure that you are connected to the internet and try again"""
    if is_numeric(obs_version) and repo_with_new_packages > 0:
        if args.machine:
            output_str += " "
        else:
            output_str += "\n"
        output_str += f"Other {repo_with_new_packages} repos may have newer versions"
    return output_str


# when imported as module, do not run
if __name__ == '__main__':
    print(main())
