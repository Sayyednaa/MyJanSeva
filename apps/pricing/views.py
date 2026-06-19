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
