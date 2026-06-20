from django.db import models
from django.conf import settings

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
