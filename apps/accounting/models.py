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
    document = models.OneToOneField(
        CustomerDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_record'
    )
    farmer_card = models.OneToOneField(
        'id_cards.FarmerIDCard',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_record'
    )
    ration_card = models.OneToOneField(
        'id_cards.RationCard',
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

    @property
    def customer(self):
        if self.document and self.document.customer:
            return self.document.customer
        
        # Find matching customer dynamically
        from apps.customers.models import Customer
        from apps.documents.views import matches_customer
        card = self.farmer_card or self.ration_card
        if card:
            for cust in Customer.objects.filter(created_by=self.operator):
                if matches_customer(card, cust):
                    return cust
        return None

    @property
    def customer_name(self):
        cust = self.customer
        if cust:
            return cust.full_name
        if self.document and self.document.customer:
            return self.document.customer.full_name
        if self.farmer_card:
            return self.farmer_card.name_en
        if self.ration_card:
            return self.ration_card.head_of_family
        return "Unknown"

    @property
    def display_document_name(self):
        if self.document:
            return self.document.name
        elif self.farmer_card:
            return self.farmer_card.display_name
        elif self.ration_card:
            return self.ration_card.display_name
        return None

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_name} - {self.service_name} ({self.payment_status})"

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
