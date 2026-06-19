"""ID Cards admin"""
from django.contrib import admin
from .models import IDCardTemplate, IDCardGeneration

@admin.register(IDCardTemplate)
class IDCardTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'card_type', 'is_active', 'created_at')
    list_filter = ('card_type', 'is_active')

@admin.register(IDCardGeneration)
class IDCardGenerationAdmin(admin.ModelAdmin):
    list_display = ('custom_name', 'user', 'template', 'created_at')
