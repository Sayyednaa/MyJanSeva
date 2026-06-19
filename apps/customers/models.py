"""Customer Vault models"""
from django.db import models
from django.conf import settings


class Customer(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='customers')
    full_name = models.CharField(max_length=120)
    father_name = models.CharField(max_length=120, blank=True)
    mother_name = models.CharField(max_length=120, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    dob = models.DateField(null=True, blank=True)
    mobile = models.CharField(max_length=15)
    alternate_mobile = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    village = models.CharField(max_length=100, blank=True)
    taluka = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=6, blank=True)
    aadhaar_number = models.CharField(max_length=14, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    voter_id = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='customers/photos/', blank=True, null=True)
    signature = models.ImageField(upload_to='customers/signatures/', blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.mobile})"

    def get_initials(self):
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return self.full_name[:2].upper()


class FamilyLink(models.Model):
    primary = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='family_links')
    member = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='linked_families')
    relation = models.CharField(max_length=50)

    class Meta:
        unique_together = ('primary', 'member')

    def __str__(self):
        return f"{self.primary.full_name} → {self.member.full_name} ({self.relation})"
