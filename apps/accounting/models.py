from django.db import models
from django.conf import settings
from apps.customers.models import Customer
from apps.documents.models import CustomerDocument

class CustomerTransaction(models.Model):
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('debt', 'Debt / Partial'),
        ('unpaid', 'Unpaid'),
    ]
    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('other', 'Other'),
    ]

    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_transactions')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='transactions')
    document = models.OneToOneField(
        CustomerDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_record'
    )
    service_name = models.CharField(max_length=150)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    payment_method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='cash')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.full_name} - {self.service_name} ({self.payment_status})"

    def save(self, *args, **kwargs):
        # Automatically calculate due amount and status
        self.due_amount = self.total_amount - self.paid_amount
        if self.paid_amount >= self.total_amount:
            self.payment_status = 'paid'
        elif self.paid_amount > 0:
            self.payment_status = 'debt'
        else:
            self.payment_status = 'unpaid'
        super().save(*args, **kwargs)
