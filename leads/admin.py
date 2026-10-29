from django.contrib import admin
from django.utils import timezone

from .models import Brief, Consultation


@admin.register(Brief)
class BriefAdmin(admin.ModelAdmin):
    list_display = ('company', 'name', 'email', 'budget', 'handled', 'created_at')
    list_filter = ('handled', 'budget')
    search_fields = ('company', 'name', 'email')
    list_editable = ('handled',)
    readonly_fields = ('handled_at', 'created_at')

    def save_model(self, request, obj, form, change):
        if 'handled' in form.changed_data:
            obj.handled_at = timezone.now() if obj.handled else None
        super().save_model(request, obj, form, change)


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('start', 'name', 'email', 'status')
    list_filter = ('status',)
    search_fields = ('name', 'email')
    actions = ['cancel']

    @admin.action(description='Cancel selected (frees the slots, keeps the records)')
    def cancel(self, request, queryset):
        updated = queryset.update(status=Consultation.Status.CANCELLED)
        self.message_user(request, f'{updated} consultation(s) cancelled.')
