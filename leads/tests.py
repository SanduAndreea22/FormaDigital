import os
import subprocess
import sys
from datetime import datetime

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Brief, Consultation
from .slots import available_slots


@override_settings(SECURE_SSL_REDIRECT=False)
class BaseTestCase(TestCase):
    def setUp(self):
        cache.clear()  # rate-limit counters live in the cache


class PagesTests(BaseTestCase):
    def test_pages_render(self):
        for name in ('home', 'services', 'portfolio', 'contact'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_security_headers(self):
        response = self.client.get(reverse('home'))
        csp = response.headers['Content-Security-Policy']
        self.assertIn("default-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn('Permissions-Policy', response.headers)

    def test_no_third_party_assets(self):
        html = self.client.get(reverse('home')).content.decode()
        self.assertNotIn('googleapis', html)
        self.assertNotIn('gstatic', html)


class BriefTests(BaseTestCase):
    data = {'name': 'Ana', 'company': 'Acme', 'email': 'Ana@Acme.ro', 'website': '',
            'budget': '3to6', 'goals': 'More leads', 'leave_empty': ''}

    def post(self, **overrides):
        return self.client.post(reverse('submit_brief'), {**self.data, **overrides})

    def test_valid_brief_saved_and_emailed(self):
        self.assertRedirects(self.post(), reverse('contact'))
        self.assertEqual(Brief.objects.get().email, 'ana@acme.ro')  # normalised
        self.assertEqual(len(mail.outbox), 1)

    def test_invalid_email_rejected(self):
        self.assertEqual(self.post(email='nope').status_code, 400)
        self.assertEqual(Brief.objects.count(), 0)

    def test_honeypot_rejected_with_visible_error(self):
        response = self.post(leave_empty='bot')
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Something went wrong', status_code=400)
        self.assertEqual(Brief.objects.count(), 0)

    def test_line_break_in_company_is_rejected_not_a_500(self):
        response = self.post(company='Evil\nBcc: x@y.z')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Brief.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_mail_failure_does_not_break_the_visitor_flow(self):
        with override_settings(EMAIL_BACKEND='leads.tests.BrokenBackend'):
            with self.assertLogs('leads', level='ERROR'):
                self.assertRedirects(self.post(), reverse('contact'))
        self.assertEqual(Brief.objects.count(), 1)

    def test_rate_limit(self):
        for i in range(5):
            self.assertEqual(self.post(company=f'Co{i}').status_code, 302)
        self.assertEqual(self.post(company='Co6').status_code, 429)
        self.assertEqual(Brief.objects.count(), 5)


class BrokenBackend:
    def __init__(self, *args, **kwargs):
        pass

    def send_messages(self, messages):
        raise ConnectionError('smtp down')


class BookingTests(BaseTestCase):
    def post(self, slot, email='ana@acme.ro', **overrides):
        return self.client.post(reverse('book_consultation'), {
            'start': timezone.localtime(slot).strftime('%Y-%m-%dT%H:%M'),
            'name': 'Ana', 'email': email, 'notes': '', 'leave_empty': '', **overrides})

    def test_book_then_slot_disappears(self):
        slot = available_slots()[0]
        self.assertRedirects(self.post(slot), reverse('contact'))
        self.assertNotIn(slot, available_slots())

    def test_double_booking_blocked(self):
        slot = available_slots()[0]
        self.post(slot)
        self.assertEqual(self.post(slot, 'other@x.ro').status_code, 400)
        self.assertEqual(Consultation.objects.count(), 1)

    def test_arbitrary_time_rejected(self):
        response = self.client.post(reverse('book_consultation'), {
            'start': '2030-01-01T03:17', 'name': 'A', 'email': 'a@b.ro'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Consultation.objects.count(), 0)

    def test_one_email_cannot_hoard_slots(self):
        slots = available_slots()
        self.assertEqual(self.post(slots[0]).status_code, 302)
        self.assertEqual(self.post(slots[1]).status_code, 302)
        self.assertEqual(self.post(slots[2]).status_code, 400)
        self.assertEqual(self.post(slots[2], 'ANA@acme.ro').status_code, 400)  # case-insensitive
        self.assertEqual(Consultation.objects.count(), 2)

    def test_line_break_in_name_rejected(self):
        self.assertEqual(self.post(available_slots()[0], name='A\nB').status_code, 400)

    def test_honeypot_rejected(self):
        self.assertEqual(self.post(available_slots()[0], leave_empty='bot').status_code, 400)
        self.assertEqual(Consultation.objects.count(), 0)

    def test_rate_limit(self):
        slot = available_slots()[0]
        for _ in range(10):
            self.post(slot, email='bad')
        self.assertEqual(self.post(slot).status_code, 429)


class AdminGridTests(TestCase):
    def local(self, *args):
        return timezone.make_aware(datetime(*args))

    def check(self, start):
        Consultation(start=start, name='A', email='a@b.ro').clean()

    def test_on_grid_ok(self):
        self.check(self.local(2030, 1, 7, 10, 30))  # Monday

    def test_off_grid_rejected(self):
        for bad in (self.local(2030, 1, 7, 10, 15), self.local(2030, 1, 5, 10, 0), self.local(2030, 1, 7, 9, 30),
                    self.local(2030, 1, 7, 17, 0)):
            with self.assertRaises(ValidationError):
                self.check(bad)


class SettingsGuardTests(TestCase):
    """Production must refuse to boot with missing secrets instead of falling back to unsafe defaults."""

    def boot(self, **env):
        base = {k: v for k, v in os.environ.items() if k not in ('SECRET_KEY', 'TEAM_EMAIL', 'DEBUG')}
        base.update({'DJANGO_SETTINGS_MODULE': 'config.settings', 'DEBUG': '0', **env})
        return subprocess.run(
            [sys.executable, '-c', 'import django; django.setup()'],
            env=base, cwd=settings.BASE_DIR, capture_output=True, text=True)

    def test_missing_secret_key_refuses_to_boot(self):
        result = self.boot(TEAM_EMAIL='t@x.ro')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SECRET_KEY', result.stderr)

    def test_missing_team_email_refuses_to_boot(self):
        result = self.boot(SECRET_KEY='x' * 60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('TEAM_EMAIL', result.stderr)

    def test_complete_env_boots(self):
        self.assertEqual(self.boot(SECRET_KEY='x' * 60, TEAM_EMAIL='t@x.ro').returncode, 0)
