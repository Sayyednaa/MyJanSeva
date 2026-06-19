"""Document Vault models"""
from django.db import models
from django.conf import settings
from apps.customers.models import Customer


class CustomerDocument(models.Model):
    CATEGORY_CHOICES = [
        ('identity', 'Identity'),
        ('education', 'Education'),
        ('land', 'Land Records'),
        ('medical', 'Medical'),
        ('other', 'Other'),
    ]
    IDENTITY_TYPES = [
        ('aadhaar', 'Aadhaar Card'),
        ('pan', 'PAN Card'),
        ('voter', 'Voter ID'),
        ('passport', 'Passport'),
        ('dl', "Driver's Licence"),
        ('other', 'Other'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    doc_type = models.CharField(max_length=20, choices=IDENTITY_TYPES, default='other')
    name = models.CharField(max_length=120)
    file = models.FileField(upload_to='documents/%Y/%m/')
    file_size = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.customer.full_name} — {self.name}"

    def is_image(self):
        return self.file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))

    def is_pdf(self):
        return self.file.name.lower().endswith('.pdf')

    def file_size_kb(self):
        return round(self.file_size / 1024, 1)
