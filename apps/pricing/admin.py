"""Pricing admin"""
from django.contrib import admin
from .models import Service, ServiceCategory


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_active', 'updated_at')
    list_filter = ('is_active', 'category')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
