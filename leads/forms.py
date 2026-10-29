import re

from django import forms

from .models import Brief

CONTROL_CHARS = re.compile(r'[\x00-\x1f\x7f]')


def single_line(value):
    """Names and companies end up in email text; line breaks there are never legitimate."""
    if CONTROL_CHARS.search(value):
        raise forms.ValidationError('Please use plain text without line breaks.')


def honeypot_field():
    """Hidden field real visitors never fill (declare it as `leave_empty` on the form)."""
    return forms.CharField(required=False, widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}))


class HoneypotMixin:
    """A generic form error is shown (not a silent failure), so a visitor whose browser
    autofilled the hidden field can still tell something went wrong."""

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('leave_empty'):
            raise forms.ValidationError('Something went wrong. Please reload the page and try again.')
        return cleaned


class BriefForm(HoneypotMixin, forms.ModelForm):
    leave_empty = honeypot_field()

    class Meta:
        model = Brief
        fields = ['name', 'company', 'email', 'website', 'budget', 'goals']
        widgets = {'goals': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ('name', 'company'):
            self.fields[field].validators.append(single_line)

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class ConsultationForm(HoneypotMixin, forms.Form):
    leave_empty = honeypot_field()

    start = forms.DateTimeField(input_formats=['%Y-%m-%dT%H:%M'])
    name = forms.CharField(max_length=120, validators=[single_line])
    email = forms.EmailField()
    notes = forms.CharField(max_length=1000, required=False, widget=forms.Textarea(attrs={'rows': 3}))

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()
