from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BriefForm, ConsultationForm
from .models import Consultation
from .slots import all_slots, grouped_available


def _notify_team(subject, body):
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.TEAM_EMAIL], fail_silently=True)


@require_POST
def submit_brief(request):
    form = BriefForm(request.POST)
    if not form.is_valid():
        return render(request, 'contact.html', {
            'brief_form': form,
            'consult_form': ConsultationForm(),
            'slot_groups': grouped_available(),
        }, status=400)
    brief = form.save()
    _notify_team(
        f'New brief from {brief.company}',
        f'Name: {brief.name}\nCompany: {brief.company}\nEmail: {brief.email}\n'
        f'Website: {brief.website or "-"}\nBudget: {brief.get_budget_display()}\n\n{brief.goals}',
    )
    messages.success(request, 'Brief received. We reply within 24 working hours with a package proposal and a starter plan.')
    return redirect('contact')


@require_POST
def book_consultation(request):
    form = ConsultationForm(request.POST)
    if form.is_valid():
        start = timezone.make_aware(form.cleaned_data['start'].replace(tzinfo=None))
        if start not in all_slots():
            form.add_error('start', 'Please pick one of the available time slots.')
        else:
            try:
                with transaction.atomic():
                    Consultation.objects.create(
                        start=start,
                        name=form.cleaned_data['name'],
                        email=form.cleaned_data['email'],
                        notes=form.cleaned_data['notes'],
                    )
            except IntegrityError:
                form.add_error('start', 'That slot was just taken. Please choose another one.')
            else:
                _notify_team(
                    f'New consultation: {start:%Y-%m-%d %H:%M}',
                    f'{form.cleaned_data["name"]} <{form.cleaned_data["email"]}>\n\n{form.cleaned_data["notes"]}',
                )
                messages.success(request, f'Consultation booked for {timezone.localtime(start):%A, %d %B at %H:%M}.')
                return redirect('contact')
    return render(request, 'contact.html', {
        'brief_form': BriefForm(),
        'consult_form': form,
        'slot_groups': grouped_available(),
    }, status=400)
