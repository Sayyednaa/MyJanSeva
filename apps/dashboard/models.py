from django.db import models
from django.conf import settings
from django.utils import timezone

class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Response'),
        ('resolved', 'Resolved'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=150)
    message = models.TextField()
    reply = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Ticket #{self.id} - {self.subject} ({self.user.username})"


class Todo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='todos')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    due_date = models.DateField(default=timezone.localdate)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['is_completed', 'due_date', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username} ({'Completed' if self.is_completed else 'Pending'})"


class PrintSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='print_settings')
    farmer_id_width = models.FloatField(default=3.22)
    farmer_id_height = models.FloatField(default=2.15)
    ration_card_width = models.FloatField(default=3.71)
    ration_card_height = models.FloatField(default=2.34)

    def __str__(self):
        return f"Print Settings for {self.user.username}"


