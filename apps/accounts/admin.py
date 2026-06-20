"""Accounts admin"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'business_name', 'city', 'is_active')
    list_filter = ('role', 'is_active', 'city')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    fieldsets = UserAdmin.fieldsets + (
        ('My Jan Seva Info', {
            'fields': ('role', 'phone', 'business_name', 'city', 'state', 'address', 'profile_photo', 'is_approved'),
        }),
    )
