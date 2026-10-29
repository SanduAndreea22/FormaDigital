from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Brief(models.Model):
    class Budget(models.TextChoices):
        UNDER_3K = 'lt3', 'Under 3,000 RON'
        MID = '3to6', '3,000 – 6,000 RON'
        HIGH = '6to10', '6,000 – 10,000 RON'
        OVER_10K = 'gt10', 'Over 10,000 RON'

    name = models.CharField(max_length=120)
    company = models.CharField(max_length=160)
    email = models.EmailField()
    website = models.URLField(blank=True)
    budget = models.CharField(max_length=8, choices=Budget.choices)
    goals = models.TextField(max_length=2000)
    handled = models.BooleanField(default=False)
    handled_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.company} — {self.name}'


class Consultation(models.Model):
    """A 30-minute call. Only one confirmed consultation can hold a start time (enforced by the
    database); cancelling keeps the record and frees the slot."""

    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    start = models.DateTimeField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.CONFIRMED)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    notes = models.TextField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start']
        constraints = [
            models.UniqueConstraint(fields=['start'], condition=Q(status='confirmed'), name='unique_confirmed_start'),
        ]

    def clean(self):
        """Admin entries must sit on the same grid the public booking page offers."""
        from . import slots

        if self.start is None:
            return
        local = timezone.localtime(self.start)
        if (
            local.weekday() >= 5
            or local.minute % slots.SLOT_MINUTES
            or local.second
            or not (slots.FIRST_SLOT <= local.time() <= slots.LAST_SLOT)
        ):
            raise ValidationError({'start': 'Start must be a working-day slot on the grid (10:00–16:30, every 30 minutes).'})

    def __str__(self):
        return f'{self.start:%Y-%m-%d %H:%M} — {self.name}'
