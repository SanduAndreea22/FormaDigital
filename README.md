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
python manage.py migrate && python manage.py createsuperuser
python manage.py runserver
python manage.py test
```

## Environment variables
`SECRET_KEY`, `DEBUG` (`0` in production), `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`,
`TEAM_EMAIL`, `DEFAULT_FROM_EMAIL`, and SMTP settings (`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`).

## Deploy (Render, manual Web Service)
Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
Start: `gunicorn config.wsgi`
