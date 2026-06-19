"""Documents admin"""
from django.contrib import admin
from .models import CustomerDocument

@admin.register(CustomerDocument)
class CustomerDocumentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'name', 'category', 'doc_type', 'uploaded_by', 'uploaded_at')
    list_filter = ('category', 'doc_type')
    search_fields = ('customer__full_name', 'name')
