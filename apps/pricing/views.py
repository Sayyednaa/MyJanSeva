"""Pricing views — admin only"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from .models import Service, ServiceCategory
from .forms import ServiceForm, ServiceCategoryForm


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            messages.error(request, 'Admin access required.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@admin_required
def service_list(request):
    services = Service.objects.select_related('category').all()
    categories = ServiceCategory.objects.all()
    return render(request, 'pricing/service_list.html', {
        'services': services,
        'categories': categories,
        'page_title': 'Service Pricing',
    })


@login_required
@admin_required
def service_create(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            form.save()
            cache.delete('service_prices')
            messages.success(request, 'Service created successfully.')
            return redirect('pricing:list')
    else:
        form = ServiceForm()
    return render(request, 'pricing/service_form.html', {'form': form, 'page_title': 'Add Service'})


@login_required
@admin_required
def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            cache.delete('service_prices')
            messages.success(request, 'Service updated.')
            return redirect('pricing:list')
    else:
        form = ServiceForm(instance=service)
    return render(request, 'pricing/service_form.html', {'form': form, 'service': service, 'page_title': 'Edit Service'})


@login_required
@admin_required
def service_toggle(request, pk):
    service = get_object_or_404(Service, pk=pk)
    service.is_active = not service.is_active
    service.save()
    cache.delete('service_prices')
    state = 'enabled' if service.is_active else 'disabled'
    messages.success(request, f'Service "{service.name}" {state}.')
    return redirect('pricing:list')


@login_required
def user_service_list(request):
    services = Service.objects.filter(is_active=True).select_related('category')
    
    # Precalculate Rupee prices
    COIN_TO_INR_RATE = 0.50
    for service in services:
        service.rupee_price = float(service.price) * COIN_TO_INR_RATE
        
    # Group services by category
    services_by_cat = {}
    for service in services:
        cat_key = (
            service.category.name,
            service.category.icon or 'bi-gear-fill',
            service.category.order if hasattr(service.category, 'order') else 999
        ) if service.category else ('General Services', 'bi-gear-fill', 999)
        
        if cat_key not in services_by_cat:
            services_by_cat[cat_key] = []
        services_by_cat[cat_key].append(service)
        
    # Sort categories by order, then name
    sorted_categories = []
    for key in sorted(services_by_cat.keys(), key=lambda x: (x[2], x[0])):
        sorted_categories.append({
            'name': key[0],
            'icon': key[1],
            'services': services_by_cat[key]
        })
        
    return render(request, 'pricing/view_pricing.html', {
        'categories': sorted_categories,
        'page_title': 'Service Pricing',
    })

