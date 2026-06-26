from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.customers.models import Customer
from apps.documents.models import CustomerDocument
from .models import CustomerTransaction
from .forms import CustomerTransactionForm

@login_required
def dashboard_view(request):
    # Operator summary metrics
    txns = CustomerTransaction.objects.filter(operator=request.user)
    
    total_paid = txns.aggregate(total=Sum('paid_amount'))['total'] or 0.00
    total_due = txns.aggregate(total=Sum('due_amount'))['total'] or 0.00
    total_txns_count = txns.count()
    
    unpaid_docs_count = txns.filter(document__isnull=False, due_amount__gt=0).count()
    
    # 1. Recent Transactions (All Ledger)
    q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    ledger_txns = txns.select_related('customer', 'document')
    if q:
        ledger_txns = ledger_txns.filter(customer__full_name__icontains=q)
    if status_filter:
        ledger_txns = ledger_txns.filter(payment_status=status_filter)
        
    paginator = Paginator(ledger_txns, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    # 2. Outstanding Debts by Customer
    # We annotate each customer who has debt to show their total unpaid balance
    debt_customers = Customer.objects.filter(
        created_by=request.user, 
        transactions__due_amount__gt=0
    ).annotate(
        total_debt=Sum('transactions__due_amount'),
        txn_count=Count('transactions')
    ).filter(total_debt__gt=0).order_by('-total_debt')
    
    # 3. Unpaid / Under-paid Documents
    unpaid_documents = CustomerDocument.objects.filter(
        customer__created_by=request.user,
        billing_record__due_amount__gt=0
    ).select_related('customer', 'billing_record').order_by('-uploaded_at')

    # Also track documents with no billing records at all (unbilled docs)
    # to let operators track what hasn't been charged yet
    unbilled_documents = CustomerDocument.objects.filter(
        customer__created_by=request.user,
        billing_record__isnull=True
    ).select_related('customer').order_by('-uploaded_at')

    active_tab = request.GET.get('tab', 'ledger')

    return render(request, 'accounting/dashboard.html', {
        'page_title': 'Accounting Ledger',
        'total_paid': total_paid,
        'total_due': total_due,
        'total_txns_count': total_txns_count,
        'unpaid_docs_count': unpaid_docs_count,
        'page_obj': page_obj,
        'query': q,
        'status_filter': status_filter,
        'debt_customers': debt_customers,
        'unpaid_documents': unpaid_documents,
        'unbilled_documents': unbilled_documents,
        'active_tab': active_tab,
    })

@login_required
def transaction_create(request):
    customer_id = request.GET.get('customer_id')
    document_id = request.GET.get('document_id')
    
    if request.method == 'POST':
        form = CustomerTransactionForm(request.POST, user=request.user)
        if form.is_valid():
            txn = form.save(commit=False)
            txn.operator = request.user
            txn.save()
            messages.success(request, f'Transaction recorded for {txn.customer.full_name}.')
            # Redirect to customer page if we came from there, otherwise accounting
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            return redirect('accounting:dashboard')
    else:
        form = CustomerTransactionForm(user=request.user, customer_id=customer_id, document_id=document_id)
        
    next_url = request.GET.get('next', '')
    return render(request, 'accounting/form.html', {
        'form': form,
        'page_title': 'Record New Service Transaction',
        'is_create': True,
        'next_url': next_url,
    })

@login_required
def transaction_update(request, pk):
    txn = get_object_or_404(CustomerTransaction, pk=pk, operator=request.user)
    
    if request.method == 'POST':
        form = CustomerTransactionForm(request.POST, instance=txn, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction details updated.')
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            return redirect('accounting:dashboard')
    else:
        form = CustomerTransactionForm(instance=txn, user=request.user)
        
    next_url = request.GET.get('next', '')
    return render(request, 'accounting/form.html', {
        'form': form,
        'page_title': 'Edit Transaction details',
        'is_create': False,
        'next_url': next_url,
    })

@login_required
def record_payment(request, pk):
    txn = get_object_or_404(CustomerTransaction, pk=pk, operator=request.user)
    if request.method == 'POST':
        try:
            from decimal import Decimal, InvalidOperation
            amount_paid_str = request.POST.get('amount_paid', '0')
            try:
                amount_paid = Decimal(amount_paid_str)
            except InvalidOperation:
                raise ValueError("Invalid payment amount.")
                
            if amount_paid <= 0:
                raise ValueError("Payment amount must be positive.")
            if amount_paid > txn.due_amount:
                raise ValueError(f"Payment amount cannot exceed outstanding debt of Rs. {txn.due_amount}.")
                
            txn.paid_amount = txn.paid_amount + amount_paid
            txn.save()
            messages.success(request, f'Payment of Rs. {amount_paid:.2f} recorded for {txn.customer.full_name}.')
        except ValueError as e:
            messages.error(request, f'Error: {str(e)}')
            
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('accounting:dashboard')
        return redirect(next_url)
        
    # Render a small form for GET requests
    next_url = request.GET.get('next', '') or request.META.get('HTTP_REFERER') or reverse('accounting:dashboard')
    return render(request, 'accounting/record_payment.html', {
        'txn': txn,
        'page_title': 'Record Customer Payment',
        'next_url': next_url,
    })

@login_required
def transaction_delete(request, pk):
    txn = get_object_or_404(CustomerTransaction, pk=pk, operator=request.user)
    customer_pk = txn.customer.pk
    
    if request.method == 'POST':
        txn.delete()
        messages.success(request, 'Transaction deleted.')
        next_url = request.POST.get('next') or reverse('accounting:dashboard')
        return redirect(next_url)
        
    next_url = request.GET.get('next', '')
    return render(request, 'accounting/confirm_delete.html', {
        'txn': txn,
        'next_url': next_url,
        'page_title': 'Confirm Delete Transaction',
    })
