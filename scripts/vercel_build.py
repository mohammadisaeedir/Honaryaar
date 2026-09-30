import os
import subprocess
import sys

unpooled = os.environ.get("DATABASE_URL_UNPOOLED")
if unpooled:
    os.environ["DATABASE_URL"] = unpooled

raise SystemExit(
    subprocess.call([sys.executable, "manage.py", "migrate", "--noinput"])
)
