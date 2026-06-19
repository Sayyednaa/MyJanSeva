"""Wallet models"""
from django.db import models
from django.conf import settings
from decimal import Decimal


class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — {self.balance} Coins"

    def has_sufficient_balance(self, amount):
        return self.balance >= Decimal(str(amount))


class WalletTransaction(models.Model):
    TYPE_CHOICES = [
        ('credit', 'Credit (Top-up)'),
        ('debit',  'Debit (Service Used)'),
        ('refund', 'Refund'),
    ]
    METHOD_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('upi',      'UPI'),
        ('qr',       'QR Payment'),
        ('manual',   'Manual / Admin'),
        ('system',   'System'),
    ]
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='system')
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    reference_id = models.CharField(max_length=100, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.wallet.user.username} — {self.transaction_type} {self.amount} Coins"


class UsageRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='usage_records')
    service_name = models.CharField(max_length=100)
    service_slug = models.CharField(max_length=100)
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} used {self.service_name} — {self.cost} Coins"


class TopUpRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='topup_requests')
    utr = models.CharField(max_length=12, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    coins = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.utr} ({self.status})"
