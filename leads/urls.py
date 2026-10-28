from django.urls import path

from . import views

urlpatterns = [
    path('brief/', views.submit_brief, name='submit_brief'),
    path('book/', views.book_consultation, name='book_consultation'),
]
