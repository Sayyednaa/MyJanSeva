"""Pricing context processor — inject active service prices"""
from django.core.cache import cache
from .models import Service


def service_prices(request):
    prices = cache.get('service_prices')
    if prices is None:
        prices = {s.slug: s for s in Service.objects.filter(is_active=True)}
        cache.set('service_prices', prices, 300)
    return {'service_prices': prices}
