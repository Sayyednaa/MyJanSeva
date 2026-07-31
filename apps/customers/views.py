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
    from django.db.models import Sum
    import re
    from apps.id_cards.models import FarmerIDCard, RationCard
    
    customer = get_object_or_404(Customer, pk=pk, created_by=request.user)
    docs = list(customer.documents.all().select_related('billing_record'))
    
    def matches_customer(card, cust):
        c_aadhaar = re.sub(r'\D', '', cust.aadhaar_number) if cust.aadhaar_number else ''
        c_mobile = re.sub(r'\D', '', cust.mobile) if cust.mobile else ''
        if hasattr(card, 'farmer_id'):
            card_aadhaar = re.sub(r'\D', '', card.aadhaar) if card.aadhaar else ''
            card_mobile = re.sub(r'\D', '', card.mobile) if card.mobile else ''
            if c_aadhaar and card_aadhaar and (c_aadhaar in card_aadhaar or card_aadhaar in c_aadhaar):
                return True
            if c_mobile and card_mobile and (c_mobile in card_mobile or card_mobile in c_mobile):
                return True
            if card.name_en and cust.full_name:
                if cust.full_name.lower() in card.name_en.lower() or card.name_en.lower() in cust.full_name.lower():
                    return True
        elif hasattr(card, 'card_number'):
            card_mobile = re.sub(r'\D', '', card.mobile) if card.mobile else ''
            if c_mobile and card_mobile and (c_mobile in card_mobile or card_mobile in c_mobile):
                return True
            if card.head_of_family and cust.full_name:
                if cust.full_name.lower() in card.head_of_family.lower() or card.head_of_family.lower() in cust.full_name.lower():
                    return True
            for member in card.family_members or []:
                m_name = member.get('name', '').lower()
                m_aadhaar = re.sub(r'\D', '', member.get('aadhaar', ''))
                if c_aadhaar and m_aadhaar and (c_aadhaar in m_aadhaar or m_aadhaar in c_aadhaar):
                    return True
                if cust.full_name and m_name:
                    if cust.full_name.lower() in m_name or m_name in cust.full_name.lower():
                        return True
        return False

    farmer_cards = FarmerIDCard.objects.filter(user=request.user)
    ration_cards = RationCard.objects.filter(user=request.user)
    
    matched_farmer = [fc for fc in farmer_cards if matches_customer(fc, customer)]
    matched_ration = [rc for rc in ration_cards if matches_customer(rc, customer)]
    
    for c in matched_farmer:
        c.customer = customer
    for c in matched_ration:
        c.customer = customer
        
    merged_docs = docs + matched_farmer + matched_ration
    
    from django.utils.timezone import now
    def get_sort_date(item):
        return getattr(item, 'doc_date', None) or now()
        
    merged_docs.sort(key=get_sort_date, reverse=True)
    docs = merged_docs[:10]
    
    usage = request.user.usage_records.filter(extra_data__customer_id=pk)[:10]
    customer_txns = customer.transactions.all()
    customer_total_paid = customer_txns.aggregate(total=Sum('paid_amount'))['total'] or 0.00
    customer_total_due = customer_txns.aggregate(total=Sum('due_amount'))['total'] or 0.00
    
    return render(request, 'customers/detail.html', {
        'customer': customer,
        'docs': docs,
        'usage': usage,
        'customer_txns': customer_txns[:10],
        'customer_total_paid': customer_total_paid,
        'customer_total_due': customer_total_due,
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
