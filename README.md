# package_last_update
An utility to get informations about a package last update

It reports the OBS version and last-change date, then cross-checks two upstream
sources: [repology.org](https://repology.org) (versions across many distros) and
[release-monitoring.org](https://release-monitoring.org) (Anitya, the latest upstream
release), so you can decide which packages need attention :)

# usage:
    $ last_update <package_name>

# examples:
    ./last_update.py gzip
    - gzip on openSUSE:Factory is 1.14 changed on Jul 01 10:04 (up to date with upstream)

    ./last_update.py k3sup
    - k3sup on openSUSE:Factory is 0.12.7 changed on Oct 05 2022
      Other 4 repos may have newer versions (newest: 0.13.0), consider updating!
      release-monitoring.org: upstream 0.13.0 (newer!)

    ./last_update.py coreutils -p Base:System
    - coreutils on Base:System is 9.3 changed on Apr 20 09:26

    ./last_update.py gzip -m
    {"package": "gzip", "project": "openSUSE:Factory", "version": "1.14", "changed": "Jul 01 10:04", "changed_epoch": 1782893040, "newer_repos": 0, "newest_version": null, "upstream_version": "1.14", "upstream_newer": false}

Use `--anitya-distro` to change the release-monitoring.org distribution name
(default: `openSUSE`; e.g. `openSUSE Tumbleweed`, `openSUSE Leap`).

Exit codes: 0 ok, 1 missing osc/rpmspec, 2 package not found, 3 network error.
(A release-monitoring.org failure only warns — it never changes the exit code.)

## how to run tests:

    $ python3 -m unittest tests/*.py


## requirements:
- a working configuration of [osc](https://en.opensuse.org/openSUSE:OSC), with authentication setup
- `rpmspec` binary (provided by openSUSE package rpm-build)  
- install dependencies using either : 
  - `zypper install python3-requests python3-packaging`

  or 

  - `pip3 install -r requirements.txt` 


