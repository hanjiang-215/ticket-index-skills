# Dependencies

This repository has no third-party runtime, build, or test dependencies.

## Runtime requirements

- Python 3.11 or newer. The index generator uses the standard-library `tomllib` module,
  which is included in Python 3.11+.
- Python standard library only. The index generator, installer, hook, tests, and verification
  script do not require packages from PyPI or another package registry.

## Dependency inventory

| Dependency | Source | Purpose | License or restriction | Install command |
| --- | --- | --- | --- | --- |
| Python standard library (`argparse`, `tomllib`, `pathlib`, `unittest`, and others) | Python 3.11+ distribution | Index parsing/rendering, installation, hooks, and tests | Distributed under the applicable Python license; no separate package is bundled | Install Python 3.11+ using your operating system's trusted Python distribution; no package install is needed |

No dependency lock file is required because the project has no external packages.

## Install and verify

```bash
python --version
python -m unittest discover -s tests -v
python scripts/verify.py
```

The first command must report Python 3.11 or newer. The other commands run the standard-
library unit suite and the complete CI verification cycle, including the demo and installer.
