from django.contrib import admin
from .models import CustomerTransaction

@admin.register(CustomerTransaction)
class CustomerTransactionAdmin(admin.ModelAdmin):
    list_display = ('customer', 'service_name', 'total_amount', 'paid_amount', 'due_amount', 'payment_status', 'created_at')
    list_filter = ('payment_status', 'payment_method', 'created_at')
    search_fields = ('customer__full_name', 'service_name')
