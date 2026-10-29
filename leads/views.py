import logging
import re
import threading
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BriefForm, ConsultationForm
from .models import Brief, Consultation
from .ratelimit import rate_limit
from .slots import all_slots, grouped_available

logger = logging.getLogger(__name__)

MAX_UPCOMING_PER_EMAIL = 2
DUPLICATE_WINDOW = timedelta(minutes=5)
BRIEF_SUCCESS = 'Brief received. We reply within 24 working hours with a package proposal and a starter plan.'


def _send_team_mail(subject, body):
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.TEAM_EMAIL])
    except Exception:
        # The lead is already saved; a mail failure must not turn into an error page for the visitor.
        logger.exception('Could not email the team: %s', subject)


def _notify_team(subject, body):
    # Header values may never contain line breaks, whatever the visitor typed.
    subject = re.sub(r'[\x00-\x1f\x7f]+', ' ', subject)
    if settings.NOTIFY_IN_BACKGROUND:
        # Non-daemon: the process waits for it at shutdown, so a deploy does not drop a mail in flight.
        threading.Thread(target=_send_team_mail, args=(subject, body)).start()
    else:
        _send_team_mail(subject, body)


def _booked_message(start):
    return f'Consultation booked for {timezone.localtime(start):%A, %d %B at %H:%M}.'


def _contact_context(brief_form=None, consult_form=None):
    return {
        'brief_form': brief_form or BriefForm(),
        'consult_form': consult_form or ConsultationForm(),
        'slot_groups': grouped_available(),
    }


@require_POST
@rate_limit('brief', limit=5, window_seconds=3600)
def submit_brief(request):
    form = BriefForm(request.POST)
    if not form.is_valid():
        return render(request, 'contact.html', _contact_context(brief_form=form), status=400)
    data = form.cleaned_data
    if Brief.objects.filter(email=data['email'], goals=data['goals'], created_at__gte=timezone.now() - DUPLICATE_WINDOW).exists():
        # Double click or resubmit: the first one already went through, so this is a success, not a new lead.
        messages.success(request, BRIEF_SUCCESS)
        return redirect('contact')
    brief = form.save()
    _notify_team(
        f'New brief from {brief.company}',
        f'Name: {brief.name}\nCompany: {brief.company}\nEmail: {brief.email}\n'
        f'Website: {brief.website or "-"}\nBudget: {brief.get_budget_display()}\n\n{brief.goals}',
    )
    messages.success(request, BRIEF_SUCCESS)
    return redirect('contact')


@require_POST
@rate_limit('book', limit=10, window_seconds=3600)
def book_consultation(request):
    form = ConsultationForm(request.POST)
    if form.is_valid():
        start = form.cleaned_data['start']  # already timezone-aware
        email = form.cleaned_data['email']
        confirmed = Consultation.objects.filter(status=Consultation.Status.CONFIRMED)
        if start not in all_slots():
            form.add_error('start', 'Please pick one of the available time slots.')
        elif confirmed.filter(start=start, email=email).exists():
            # Double click: this visitor already holds the slot.
            messages.success(request, _booked_message(start))
            return redirect('contact')
        elif confirmed.filter(email=email, start__gt=timezone.now()).count() >= MAX_UPCOMING_PER_EMAIL:
            form.add_error(None, f'You already have {MAX_UPCOMING_PER_EMAIL} upcoming consultations booked with this email.')
        else:
            try:
                with transaction.atomic():
                    Consultation.objects.create(
                        start=start,
                        name=form.cleaned_data['name'],
                        email=email,
                        notes=form.cleaned_data['notes'],
                    )
            except IntegrityError:
                form.add_error('start', 'That slot was just taken. Please choose another one.')
            else:
                _notify_team(
                    f'New consultation: {start:%Y-%m-%d %H:%M}',
                    f'{form.cleaned_data["name"]} <{email}>\n\n{form.cleaned_data["notes"]}',
                )
                messages.success(request, _booked_message(start))
                return redirect('contact')
    return render(request, 'contact.html', _contact_context(consult_form=form), status=400)
