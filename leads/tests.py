import os
import subprocess
import sys
from datetime import datetime

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Brief, Consultation
from .slots import _slots_for, all_slots, available_slots


@override_settings(SECURE_SSL_REDIRECT=False, NOTIFY_IN_BACKGROUND=False)
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

    def test_double_submit_guard_script_is_served(self):
        html = self.client.get(reverse('home')).content.decode()
        self.assertIn('js/forms.js', html)

    def test_favicon_is_declared_so_browsers_skip_the_404(self):
        self.assertIn('rel="icon"', self.client.get(reverse('home')).content.decode())

    def test_every_font_file_referenced_by_css_exists(self):
        import re
        from pathlib import Path

        css = (settings.BASE_DIR / 'static/css/fonts.css').read_text()
        referenced = re.findall(r"url\('\.\./fonts/([^']+)'\)", css)
        self.assertTrue(referenced)
        for name in referenced:
            self.assertTrue(Path(settings.BASE_DIR / 'static/fonts' / name).is_file(), name)

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

    def test_double_submit_creates_one_lead_and_still_succeeds(self):
        self.assertEqual(self.post().status_code, 302)
        response = self.post(name='Ana (again)')
        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(Brief.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_same_email_different_goals_is_a_new_brief(self):
        self.post()
        self.post(goals='A different project')
        self.assertEqual(Brief.objects.count(), 2)

    def test_rate_limit(self):
        for i in range(5):
            self.assertEqual(self.post(company=f'Co{i}', goals=f'Goal {i}').status_code, 302)
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

    def test_double_click_by_same_visitor_is_success_not_error(self):
        slot = available_slots()[0]
        self.post(slot)
        response = self.post(slot)
        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(Consultation.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_cancelled_slot_can_be_booked_again(self):
        slot = available_slots()[0]
        self.post(slot)
        Consultation.objects.update(status=Consultation.Status.CANCELLED)
        self.assertIn(slot, available_slots())
        self.assertEqual(self.post(slot, 'other@x.ro').status_code, 302)
        self.assertEqual(Consultation.objects.count(), 2)

    def test_cancelled_consultations_do_not_count_toward_the_email_cap(self):
        slots = available_slots()
        for slot in slots[:2]:
            self.post(slot)
        Consultation.objects.update(status=Consultation.Status.CANCELLED)
        self.assertEqual(self.post(slots[2]).status_code, 302)

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


class SlotGridTests(TestCase):
    def test_grid_is_cached_per_day_and_unchanged(self):
        _slots_for.cache_clear()
        first = all_slots()
        hits_before = _slots_for.cache_info().hits
        second = all_slots()
        self.assertEqual(first, second)
        self.assertEqual(_slots_for.cache_info().hits, hits_before + 1)

    def test_grid_shape(self):
        slots = all_slots()
        self.assertTrue(all(timezone.localtime(s).weekday() < 5 for s in slots))
        self.assertTrue(all(timezone.localtime(s).minute in (0, 30) for s in slots))
        self.assertGreater(slots[0], timezone.now())

    def test_returned_list_is_a_copy(self):
        all_slots().clear()
        self.assertTrue(all_slots())


@override_settings(NOTIFY_IN_BACKGROUND=True)
class BackgroundNotifyTests(TestCase):
    def test_mail_is_sent_from_a_thread_and_the_request_still_succeeds(self):
        import threading

        before = threading.active_count()
        with override_settings(SECURE_SSL_REDIRECT=False):
            response = self.client.post(reverse('submit_brief'), {
                'name': 'Ana', 'company': 'Acme', 'email': 'ana@acme.ro', 'website': '',
                'budget': '3to6', 'goals': 'More leads', 'leave_empty': ''})
        for t in threading.enumerate():
            if t is not threading.main_thread():
                t.join(timeout=5)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertGreaterEqual(before, 1)


class DatabaseConstraintTests(TestCase):
    """The view checks are a convenience; the database is what actually prevents double booking."""

    def make(self, start, status='confirmed'):
        return Consultation.objects.create(start=start, name='A', email='a@b.ro', status=status)

    def test_two_confirmed_on_same_start_rejected_by_db(self):
        start = available_slots()[0]
        self.make(start)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make(start)

    def test_cancelled_does_not_block_a_new_confirmed(self):
        start = available_slots()[0]
        self.make(start, status='cancelled')
        self.make(start)
        self.assertEqual(Consultation.objects.filter(start=start).count(), 2)


@override_settings(SECURE_SSL_REDIRECT=False)
class AdminTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser('boss', 'boss@x.ro', 'pw-12345-long')
        self.client.force_login(user)

    def test_cancel_action_frees_slot_and_keeps_record(self):
        start = available_slots()[0]
        c = Consultation.objects.create(start=start, name='A', email='a@b.ro')
        self.client.post(reverse('admin:leads_consultation_changelist'),
                         {'action': 'cancel', '_selected_action': [c.pk]})
        c.refresh_from_db()
        self.assertEqual(c.status, 'cancelled')
        self.assertIn(start, available_slots())

    def test_handled_at_is_stamped_and_cleared(self):
        brief = Brief.objects.create(name='A', company='C', email='a@b.ro', budget='lt3', goals='g')
        url = reverse('admin:leads_brief_change', args=[brief.pk])
        data = {'name': 'A', 'company': 'C', 'email': 'a@b.ro', 'website': '', 'budget': 'lt3', 'goals': 'g', 'handled': 'on'}
        self.client.post(url, data)
        brief.refresh_from_db()
        self.assertTrue(brief.handled)
        self.assertIsNotNone(brief.handled_at)
        data.pop('handled')
        self.client.post(url, data)
        brief.refresh_from_db()
        self.assertIsNone(brief.handled_at)


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
        base = {k: v for k, v in os.environ.items() if k not in ('SECRET_KEY', 'TEAM_EMAIL', 'DEBUG', 'DATABASE_URL')}
        base.update({'DJANGO_SETTINGS_MODULE': 'config.settings', 'DEBUG': '0', 'DATABASE_URL': 'sqlite:///:memory:', **env})
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

    def test_missing_database_url_refuses_to_boot(self):
        result = self.boot(SECRET_KEY='x' * 60, TEAM_EMAIL='t@x.ro', DATABASE_URL='')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DATABASE_URL', result.stderr)

    def test_complete_env_boots(self):
        self.assertEqual(self.boot(SECRET_KEY='x' * 60, TEAM_EMAIL='t@x.ro').returncode, 0)
