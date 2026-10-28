#!/usr/bin/env bash
# Run from your Mac after the host admin forwards 80/443.
set -euo pipefail
IP="${1:-142.44.243.231}"
echo "Checking http://$IP/ with Host: honaryaar.ir"
code=$(curl -s -o /tmp/honaryaar_public_check.html -w "%{http_code}" --max-time 15 \
  -H "Host: honaryaar.ir" "http://$IP/")
echo "HTTP $code"
head -c 200 /tmp/honaryaar_public_check.html; echo
if [[ "$code" == "200" ]]; then
  echo "OK — public HTTP reaches the app. Next: Cloudflare DNS + certbot."
  exit 0
fi
echo "Not ready yet (want 200). If timeout: ports not forwarded. If 403: host still serving its own page."
exit 1
