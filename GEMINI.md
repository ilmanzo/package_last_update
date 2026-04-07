# Project Overview

`package_last_update` is a Python-based utility designed to track and compare package versions across different repositories. Its primary purpose is to help openSUSE maintainers identify when their packages in the openSUSE Build Service (OBS) are lagging behind the latest versions available elsewhere (e.g., on Repology).

## Key Technologies
- **Python 3**: Main application logic (`last_update.py`).
- **Shell (Bash)**: Helper scripts for bulk operations and automation.
- **OBS (Open Build Service)**: Integration via the `osc` CLI tool and `rpmspec`.
- **Repology API**: Used to query the latest global versions of packages.

## Architecture
- **Core Logic**: `last_update.py` handles CLI arguments, interacts with `osc` to fetch current OBS versions, and queries the Repology API for comparison.
- **Bulk Processing**: Several shell scripts (`shouldIupdate.sh`, `shouldIupdate_serial.sh`) automate querying multiple packages (e.g., all packages owned by the user in OBS).
- **Testing**: A dedicated `tests/` directory contains unit tests for core utilities like date parsing.

# Building and Running

## Prerequisites
The following external tools must be installed and available in your `$PATH`:
- `osc`: The Open Build Service command-line tool.
- `rpmspec`: Part of the `rpm-build` package (on openSUSE).

## Installation
Install Python dependencies:
```bash
pip3 install requests packaging
```
*Note: Although `requirements.txt` mentions `semantic_version`, the current codebase uses `packaging.version`.*

## Running the Tool
To check a single package:
```bash
./last_update.py <package_name>
```

To check all your packages in OBS (sequentially):
```bash
./shouldIupdate.sh
```

## Running Tests
Tests use the standard Python `unittest` framework:
```bash
python3 -m unittest tests/*.py
```

# Development Conventions

## Coding Style
- **Python**: Follows standard PEP 8 conventions. The main script uses `argparse` for CLI management and `subprocess` for external tool interaction.
- **Shell**: Simple Bash scripts are used for orchestration.

## Testing Practices
- Unit tests are located in the `tests/` directory.
- Use `unittest` for Python code.
- Always verify that the `osc` and `rpmspec` commands are available before execution.

## Dependencies Inconsistency
- `last_update.py` imports `packaging`, but `requirements.txt` and `README.md` list `semantic_version`. Prefer installing `packaging` for the code to run correctly.
