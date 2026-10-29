from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core import views

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('', views.home, name='home'),
    path('services/', views.services, name='services'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('contact/', views.contact, name='contact'),
    path('', include('leads.urls')),
]
