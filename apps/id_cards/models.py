"""ID Card Studio models"""
from django.db import models
from django.conf import settings
from apps.customers.models import Customer


class IDCardTemplate(models.Model):
    CARD_TYPES = [
        ('aadhaar_pvc', 'Aadhaar PVC'),
        ('pan_pvc', 'PAN PVC'),
        ('voter_pvc', 'Voter PVC'),
        ('apaar', 'APAAR Card'),
        ('ayushman', 'Ayushman Bharat'),
        ('school_id', 'School ID'),
        ('employee_id', 'Employee ID'),
        ('visitor_id', 'Visitor ID'),
        ('custom', 'Custom'),
    ]
    name = models.CharField(max_length=100)
    card_type = models.CharField(max_length=20, choices=CARD_TYPES)
    description = models.TextField(blank=True)
    front_bg_color = models.CharField(max_length=7, default='#1a237e')
    back_bg_color = models.CharField(max_length=7, default='#283593')
    accent_color = models.CharField(max_length=7, default='#ffca28')
    has_qr = models.BooleanField(default=False)
    has_barcode = models.BooleanField(default=False)
    preview_image = models.ImageField(upload_to='id_card_templates/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.card_type})"


class IDCardGeneration(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='id_cards')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    template = models.ForeignKey(IDCardTemplate, on_delete=models.SET_NULL, null=True)
    custom_name = models.CharField(max_length=120, blank=True)
    front_image = models.ImageField(upload_to='id_cards/generated/', blank=True, null=True)
    back_image = models.ImageField(upload_to='id_cards/generated/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='id_cards/pdfs/', blank=True, null=True)
    cost_charged = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.custom_name or (self.customer.full_name if self.customer else 'Unknown')} — {self.template}"
