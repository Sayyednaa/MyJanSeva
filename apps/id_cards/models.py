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


class FarmerIDCard(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farmer_id_cards')
    farmer_id = models.CharField(max_length=50)
    name_en = models.CharField(max_length=150)
    name_hi = models.CharField(max_length=150, blank=True)
    dob = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    aadhaar = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    photo = models.TextField(blank=True)  # Store Base64 photo string directly
    land_details = models.JSONField(default=list, blank=True)  # JSON array of land table rows
    print_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name_en} ({self.farmer_id}) - {self.user.username}"


class RationCard(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ration_cards')
    card_number = models.CharField(max_length=50) # ration card number
    fare_shop_number = models.CharField(max_length=50, blank=True)
    scheme_name = models.CharField(max_length=50, blank=True)
    head_of_family = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    issue_date = models.CharField(max_length=20, blank=True)
    photo = models.TextField(blank=True)  # Base64 photo string
    family_members = models.JSONField(default=list, blank=True)  # List of member dicts
    design_style = models.CharField(max_length=20, default='1')
    print_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.card_number} ({self.head_of_family}) - {self.user.username}"


