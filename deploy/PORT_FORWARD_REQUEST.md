# Production edge (current)

Public site is live via **Nginx Proxy Manager** on the host, not certbot on the guest.

## Proxy Host (manager)

- Domains: `honaryaar.ir`, `www.honaryaar.ir`
- Forward to: `10.88.0.11:80` (guest WireGuard IP)
- Force SSL + HTTP/2 on NPM
- Let’s Encrypt on NPM (auto-renew; valid through ~2027-01-25)
- Do **not** run certbot on the chamedoon VM

## Cloudflare (Saeed)

- A records for apex + `www` → `142.44.243.231`, proxied (orange cloud)
- SSL/TLS mode: **Full**
- Leave `media.honaryaar.ir` as-is unless media cutover is planned

## Django on guest (`/var/www/honaryaar`)

Already configured:

- `ALLOWED_HOSTS` includes `honaryaar.ir`, `www.honaryaar.ir`, `.honaryaar.ir`
- `CSRF_TRUSTED_ORIGINS` includes `https://honaryaar.ir`, `https://www.honaryaar.ir`
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
- `DJANGO_DEBUG=false`

## Later

After a few stable days, pause the Vercel project (keep it for rollback).
