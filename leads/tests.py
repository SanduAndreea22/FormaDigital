from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Brief, Consultation
from .slots import available_slots


class PagesTests(TestCase):
    def test_pages_render(self):
        for name in ('home', 'services', 'portfolio', 'contact'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)


class BriefTests(TestCase):
    data = {'name': 'Ana', 'company': 'Acme', 'email': 'ana@acme.ro', 'website': '',
            'budget': '3to6', 'goals': 'More leads', 'nickname': ''}

    def test_valid_brief_saved_and_emailed(self):
        r = self.client.post(reverse('submit_brief'), self.data)
        self.assertRedirects(r, reverse('contact'))
        self.assertEqual(Brief.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_invalid_email_rejected(self):
        r = self.client.post(reverse('submit_brief'), {**self.data, 'email': 'nope'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Brief.objects.count(), 0)

    def test_honeypot_rejected(self):
        r = self.client.post(reverse('submit_brief'), {**self.data, 'nickname': 'bot'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Brief.objects.count(), 0)


class BookingTests(TestCase):
    def _post(self, slot, email='ana@acme.ro'):
        return self.client.post(reverse('book_consultation'), {
            'start': timezone.localtime(slot).strftime('%Y-%m-%dT%H:%M'),
            'name': 'Ana', 'email': email, 'notes': '', 'nickname': ''})

    def test_book_then_slot_disappears(self):
        slot = available_slots()[0]
        self.assertRedirects(self._post(slot), reverse('contact'))
        self.assertNotIn(slot, available_slots())

    def test_double_booking_blocked(self):
        slot = available_slots()[0]
        self._post(slot)
        r = self._post(slot, 'other@x.ro')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Consultation.objects.count(), 1)

    def test_arbitrary_time_rejected(self):
        r = self.client.post(reverse('book_consultation'), {
            'start': '2030-01-01T03:17', 'name': 'A', 'email': 'a@b.ro', 'nickname': ''})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Consultation.objects.count(), 0)
