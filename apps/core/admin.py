from django.contrib import admin

from .models import AuditLog, Company, Notification, NumberSequence, Role, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'company', 'is_active', 'is_staff')
    list_filter = ('role', 'company', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'description')
    search_fields = ('name', 'code')


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'legal_name', 'tax_id', 'base_currency', 'is_default', 'is_active')


@admin.register(NumberSequence)
class NumberSequenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefix', 'padding', 'last_number')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model', 'object_id', 'created_at')
    list_filter = ('action', 'model')
    search_fields = ('user__username', 'action', 'model', 'object_id', 'details')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read',)