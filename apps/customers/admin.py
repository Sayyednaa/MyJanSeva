"""Customers admin"""
from django.contrib import admin
from .models import Customer, FamilyLink


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'mobile', 'aadhaar_number', 'pan_number', 'created_by', 'created_at')
    list_filter = ('state', 'district')
    search_fields = ('full_name', 'mobile', 'aadhaar_number', 'pan_number')


@admin.register(FamilyLink)
class FamilyLinkAdmin(admin.ModelAdmin):
    list_display = ('primary', 'member', 'relation')
