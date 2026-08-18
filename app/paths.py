import os
import sys


def resource_path(*parts: str) -> str:
    """Resolve a path to a bundled resource (templates/, static/).

    In normal (source) runs, resolves relative to the project root. Inside a
    PyInstaller-frozen exe, `--add-data` bundles land under `sys._MEIPASS`
    (a temp extraction dir) instead — the project root doesn't exist there.
    """
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)
