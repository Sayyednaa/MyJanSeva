"""ID Card Studio views"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def farmer_id_workspace(request):
    from apps.pricing.models import Service
    try:
        service = Service.objects.get(slug='farmer-id')
        price = float(service.price)
    except Service.DoesNotExist:
        price = 50.0
        
    return render(request, 'id_cards/farmer_workspace.html', {
        'page_title': 'Farmer ID Studio',
        'farmer_id_price': price,
    })
