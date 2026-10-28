from django import forms

from .models import Brief


class BriefForm(forms.ModelForm):
    # Honeypot: real visitors never see or fill this field.
    nickname = forms.CharField(required=False, widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}))

    class Meta:
        model = Brief
        fields = ['name', 'company', 'email', 'website', 'budget', 'goals']
        widgets = {'goals': forms.Textarea(attrs={'rows': 4})}

    def clean_nickname(self):
        if self.cleaned_data['nickname']:
            raise forms.ValidationError('Spam detected.')
        return ''


class ConsultationForm(forms.Form):
    start = forms.DateTimeField(input_formats=['%Y-%m-%dT%H:%M'])
    name = forms.CharField(max_length=120)
    email = forms.EmailField()
    notes = forms.CharField(max_length=1000, required=False, widget=forms.Textarea(attrs={'rows': 3}))
    nickname = forms.CharField(required=False)

    def clean_nickname(self):
        if self.cleaned_data['nickname']:
            raise forms.ValidationError('Spam detected.')
        return ''
