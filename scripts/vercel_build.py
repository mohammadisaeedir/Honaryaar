import os
import subprocess
import sys

unpooled = os.environ.get("DATABASE_URL_UNPOOLED")
if unpooled:
    os.environ["DATABASE_URL"] = unpooled

migrate = subprocess.call([sys.executable, "manage.py", "migrate", "--noinput"])
if migrate != 0:
    raise SystemExit(migrate)

username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
if not username or not password:
    raise SystemExit(0)

email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
script = """
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ["DJANGO_SUPERUSER_USERNAME"]
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]
user, created = User.objects.get_or_create(
    username=username,
    defaults={"email": email, "is_staff": True, "is_superuser": True},
)
user.email = email
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()
print("superuser", "created" if created else "updated")
"""
raise SystemExit(
    subprocess.call([sys.executable, "manage.py", "shell", "-c", script])
)
