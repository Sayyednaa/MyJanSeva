"""Pricing engine models"""
from django.db import models


class ServiceCategory(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, default='bi-gear', help_text='Bootstrap icon class')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Service Categories'

    def __str__(self):
        return self.name


class Service(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='services')
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, default='bi-star', help_text='Bootstrap icon class')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} — {self.price} Coins"

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
