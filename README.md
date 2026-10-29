# Forma Digital

Fictional demo agency site (English), part of the Andreea Tech portfolio. Django + PostgreSQL.

- Pages: Home, Services, Portfolio, Contact
- Brief form (validated, honeypot, emails the team) and 30-minute consultation booking
  (unique slot constraint prevents double booking)
- Admin at `/admin/` for briefs and consultations
- Design direction: `design/brand.md`, static mock: `design/mock.html`

## Run locally
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # contains DEBUG=1 for local work
python manage.py migrate && python manage.py createsuperuser
python manage.py runserver
python manage.py test
```

## Environment variables
`DEBUG` is off unless set to `1`. With `DEBUG=0` the app **refuses to start** without:
`SECRET_KEY` and `TEAM_EMAIL` (where briefs and bookings are emailed).

Production also needs: `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL` (Postgres, SSL required
unless `DB_SSL_REQUIRE=0`), SMTP (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`DEFAULT_FROM_EMAIL`). Email never falls back to the console outside `DEBUG`.

Optional: `ADMIN_URL` (move the admin off `/admin/`, keep the trailing slash), `HSTS_SECONDS`
(default 3600; raise once HTTPS is confirmed), `HSTS_INCLUDE_SUBDOMAINS=1`, `HSTS_PRELOAD=1`.

## Security notes
- Fonts are self-hosted (`static/fonts`); no third-party requests. A strict CSP and Permissions-Policy are set
  by `config/middleware.py` (not applied to the admin).
- Public forms are rate limited per IP (briefs 5/hour, bookings 10/hour) and one email can hold at most
  2 upcoming consultations. Limits use the Django cache (per process); use a shared cache if you run
  several workers.
- Not covered: email verification for bookings, admin 2FA/login throttling.

## Deploy (Render, manual Web Service)
Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
Start: `gunicorn config.wsgi`
