import os
import sys


def _default_database_url() -> str:
    # A frozen (PyInstaller) exe's CWD isn't reliable, so default to a
    # myoffer.db file sitting next to the .exe itself — that also means if
    # the user runs the .exe from inside a cloud-synced folder (OneDrive,
    # 坚果云, etc.), the database file syncs along with it automatically.
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = "."
    db_path = os.path.join(base_dir, "myoffer.db").replace(os.sep, "/")
    return f"sqlite:///{db_path}"


USERNAME = os.environ.get("MYOFFER_USERNAME", "admin")
PASSWORD = os.environ.get("MYOFFER_PASSWORD", "myoffer")
SECRET_KEY = os.environ.get("MYOFFER_SECRET_KEY", "dev-secret-change-in-production")
DATABASE_URL = os.environ.get("MYOFFER_DATABASE_URL", _default_database_url())
