from django.db import models


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.company} — {self.name}'


class Consultation(models.Model):
    """A 30-minute call. The unique start time makes double booking impossible."""

    start = models.DateTimeField(unique=True)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    notes = models.TextField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start']

    def __str__(self):
        return f'{self.start:%Y-%m-%d %H:%M} — {self.name}'
