from django.shortcuts import render

from leads.forms import BriefForm, ConsultationForm
from leads.slots import grouped_available

from . import content


def home(request):
    return render(request, 'home.html', {
        'services': content.SERVICES, 'packages': content.PACKAGES,
        'cases': content.CASE_STUDIES, 'process': content.PROCESS,
        'brief_form': BriefForm(),
    })


def services(request):
    return render(request, 'services.html', {'services': content.SERVICES, 'packages': content.PACKAGES})


def portfolio(request):
    return render(request, 'portfolio.html', {'cases': content.CASE_STUDIES})


def contact(request):
    return render(request, 'contact.html', {
        'brief_form': BriefForm(), 'consult_form': ConsultationForm(),
        'slot_groups': grouped_available(),
    })
