from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import Consultation

DAYS_AHEAD = 14
FIRST_SLOT = time(10, 0)
LAST_SLOT = time(16, 30)
SLOT_MINUTES = 30


def _aware(dt):
    return timezone.make_aware(dt, timezone.get_current_timezone())


def all_slots(now=None):
    """Every bookable 30-minute start on working days in the next two weeks."""
    now = now or timezone.localtime()
    slots = []
    for offset in range(1, DAYS_AHEAD + 1):
        day = (now + timedelta(days=offset)).date()
        if day.weekday() >= 5:
            continue
        current = datetime.combine(day, FIRST_SLOT)
        end = datetime.combine(day, LAST_SLOT)
        while current <= end:
            slots.append(_aware(current))
            current += timedelta(minutes=SLOT_MINUTES)
    return slots


def available_slots():
    slots = all_slots()
    if not slots:
        return []
    taken = set(Consultation.objects.filter(start__in=slots).values_list('start', flat=True))
    return [s for s in slots if s not in taken]


def grouped_available():
    """[(date, [datetime, ...]), ...] for the template."""
    groups = {}
    for slot in available_slots():
        groups.setdefault(timezone.localtime(slot).date(), []).append(slot)
    return sorted(groups.items())
