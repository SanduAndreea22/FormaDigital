from django.contrib import admin

from .models import Brief, Consultation


@admin.register(Brief)
class BriefAdmin(admin.ModelAdmin):
    list_display = ('company', 'name', 'email', 'budget', 'handled', 'created_at')
    list_filter = ('handled', 'budget')
    search_fields = ('company', 'name', 'email')
    list_editable = ('handled',)


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('start', 'name', 'email')
    search_fields = ('name', 'email')
