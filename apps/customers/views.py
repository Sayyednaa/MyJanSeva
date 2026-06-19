"""Customer Vault views"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from .models import Customer
from .forms import CustomerForm


@login_required
def customer_list(request):
    q = request.GET.get('q', '')
    customers = Customer.objects.filter(created_by=request.user)
    if q:
        customers = customers.filter(
            Q(full_name__icontains=q) | Q(mobile__icontains=q) |
            Q(aadhaar_number__icontains=q) | Q(pan_number__icontains=q)
        )
    paginator = Paginator(customers, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'customers/list.html', {
        'page_obj': page,
        'query': q,
        'total': customers.count(),
        'page_title': 'Customer Vault',
    })


@login_required
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            messages.success(request, f'Customer "{customer.full_name}" added.')
            return redirect('customers:detail', pk=customer.pk)
    else:
        form = CustomerForm()
    return render(request, 'customers/form.html', {'form': form, 'page_title': 'Add Customer'})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk, created_by=request.user)
    docs = customer.documents.all()[:10]
    usage = request.user.usage_records.filter(extra_data__customer_id=pk)[:10]
    return render(request, 'customers/detail.html', {
        'customer': customer,
        'docs': docs,
        'usage': usage,
        'page_title': customer.full_name,
    })


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk, created_by=request.user)
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated.')
            return redirect('customers:detail', pk=pk)
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'customers/form.html', {'form': form, 'customer': customer, 'page_title': 'Edit Customer'})


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk, created_by=request.user)
    if request.method == 'POST':
        name = customer.full_name
        customer.delete()
        messages.success(request, f'Customer "{name}" deleted.')
        return redirect('customers:list')
    return render(request, 'customers/confirm_delete.html', {'customer': customer, 'page_title': 'Delete Customer'})


@login_required
def customer_search_ajax(request):
    """Quick search for AJAX calls from other modules"""
    q = request.GET.get('q', '')
    results = []
    if q and len(q) >= 2:
        customers = Customer.objects.filter(
            created_by=request.user
        ).filter(
            Q(full_name__icontains=q) | Q(mobile__icontains=q)
        )[:10]
        results = [{'id': c.pk, 'name': c.full_name, 'mobile': c.mobile, 'initials': c.get_initials()} for c in customers]
    return JsonResponse({'results': results})
