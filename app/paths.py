"""Where the program keeps config and data, in development and once frozen.

Until now both locations were derived from ``__file__``. That is correct
while the program runs from a checkout, and wrong the moment it is packaged:
``__file__`` then points inside the one-folder bundle, and a bundle installed
under ``Program Files`` is not writable. Alarm history and the settings store
would fail on the customer's panel while working perfectly on every
development machine -- a defect that only a packaged run can show.

So: frozen runs keep their writable state under ``%ProgramData%``, checkouts
keep using the repository folders, and both can be overridden with an
environment variable for tests and for unusual installs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: Repository root (this file lives in ``app/``).
_REPO_ROOT = Path(__file__).resolve().parent.parent

#: Vendor/product folder under %ProgramData%. Matches the installer layout.
_PROGRAMDATA_SUBDIR = Path("Bufera") / "MakineEkrani"


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def _programdata_root() -> Path:
    base = os.environ.get("ProgramData") or os.environ.get("ALLUSERSPROFILE")
    if base:
        return Path(base) / _PROGRAMDATA_SUBDIR
    # Non-Windows development box: keep everything beside the repository.
    return _REPO_ROOT


def _resolve(env_var: str, folder: str) -> Path:
    override = os.environ.get(env_var)
    if override:
        return Path(override)
    if is_frozen():
        return _programdata_root() / folder
    return _REPO_ROOT / folder


def config_dir() -> Path:
    """Folder holding ``opcua.json``. Override: ``BUFERA_CONFIG_DIR``."""
    return _resolve("BUFERA_CONFIG_DIR", "config")


def data_dir() -> Path:
    """Folder holding the SQLite database. Override: ``BUFERA_DATA_DIR``."""
    return _resolve("BUFERA_DATA_DIR", "data")
