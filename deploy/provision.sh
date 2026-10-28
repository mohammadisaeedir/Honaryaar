#!/usr/bin/env bash
# Run on the VPS as a sudo-capable user after the app tree is at /var/www/honaryaar
# and /var/www/honaryaar/.env is in place (mode 600).
set -euo pipefail

APP_DIR=/var/www/honaryaar
APP_USER=honaryaar

if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "Missing $APP_DIR/.env" >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo -n bash "$0" "$@"
fi

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  python3 python3-pip python3-venv python3-dev build-essential \
  nginx redis-server certbot python3-certbot-nginx \
  libjpeg-dev zlib1g-dev libffi-dev libssl-dev

systemctl enable --now redis-server

mkdir -p "$APP_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

sudo -u "$APP_USER" bash -lc "
  cd '$APP_DIR'
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
  .venv/bin/python manage.py migrate --noinput
  .venv/bin/python manage.py collectstatic --noinput
"

install -m 644 "$APP_DIR/deploy/honaryaar.service" /etc/systemd/system/honaryaar.service
install -m 644 "$APP_DIR/deploy/nginx-honaryaar.conf" /etc/nginx/sites-available/honaryaar
ln -sfn /etc/nginx/sites-available/honaryaar /etc/nginx/sites-enabled/honaryaar
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable --now honaryaar
systemctl enable --now nginx

nginx -t
systemctl reload nginx

echo "App is up on http://127.0.0.1 via Nginx."
echo "Next: point DNS A records to this server, then:"
echo "  sudo certbot --nginx -d honaryaar.ir -d www.honaryaar.ir"
