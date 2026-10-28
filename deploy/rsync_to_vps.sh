#!/usr/bin/env bash
# Usage: ./deploy/rsync_to_vps.sh [USER@HOST] [ssh_key]
# Defaults match the chamedoon VPS tunnel.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-chamedoon@chamedoon.bigde.li}"
KEY="${2:-$HOME/.ssh/id_ed25519}"
PORT="${SSH_PORT:-22402}"
REMOTE_DIR=/var/www/honaryaar
SSH_OPTS=(-p "$PORT" -i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new)

if [[ ! -f "$ROOT/deploy/.env.production" ]]; then
  python3 "$ROOT/deploy/build_server_env.py"
fi

ssh "${SSH_OPTS[@]}" "$TARGET" "sudo mkdir -p '$REMOTE_DIR' && sudo chown -R \$USER:\$USER '$REMOTE_DIR'"

rsync -az --delete \
  -e "ssh -p $PORT -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.DS_Store' \
  --exclude '/media/' \
  --exclude '/staticfiles/' \
  --exclude '.env' \
  --exclude '.env.local' \
  --exclude 'deploy/.env.production' \
  "$ROOT/" "$TARGET:$REMOTE_DIR/"

scp -P "$PORT" -i "$KEY" -o IdentitiesOnly=yes \
  "$ROOT/deploy/.env.production" "$TARGET:$REMOTE_DIR/.env"

ssh "${SSH_OPTS[@]}" "$TARGET" "chmod 600 '$REMOTE_DIR/.env' && bash '$REMOTE_DIR/deploy/provision.sh'"

echo "Deploy finished. Configure DNS then run certbot on the server."
