"""Wallet views"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Wallet, WalletTransaction, UsageRecord, TopUpRequest
from .services import WalletService, InsufficientBalanceError
from apps.pricing.models import Service


@login_required
def wallet_dashboard(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    recent_txns = WalletTransaction.objects.filter(wallet=wallet)[:5]
    recent_usage = UsageRecord.objects.filter(user=request.user)[:5]
    return render(request, 'wallet/dashboard.html', {
        'wallet': wallet,
        'recent_txns': recent_txns,
        'recent_usage': recent_usage,
        'page_title': 'My Wallet',
    })


@login_required
def transaction_history(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    txn_list = WalletTransaction.objects.filter(wallet=wallet)
    paginator = Paginator(txn_list, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'wallet/transactions.html', {
        'page_obj': page,
        'wallet': wallet,
        'page_title': 'Transaction History',
    })


@login_required
def usage_history(request):
    usage_list = UsageRecord.objects.filter(user=request.user)
    paginator = Paginator(usage_list, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'wallet/usage.html', {
        'page_obj': page,
        'page_title': 'Usage History',
    })


@login_required
def topup_view(request):
    packages = [
        {'coins': 100, 'price': 50, 'label': '100 Coins (₹50)'},
        {'coins': 1000, 'price': 500, 'label': '1000 Coins (₹500)'},
        {'coins': 500, 'price': 1000, 'label': '500 Coins (₹1000)'},
    ]
    if request.method == 'POST':
        coins = request.POST.get('coins')
        amount = request.POST.get('amount')
        utr = request.POST.get('utr', '').strip()
        
        if not coins or not amount or not utr:
            messages.error(request, 'All fields (Package, Amount, UTR) are required.')
            return redirect('wallet:topup')
            
        try:
            coins = int(coins)
            amount = float(amount)
            if coins <= 0 or amount <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, 'Invalid coins or amount format.')
            return redirect('wallet:topup')
            
        import re
        if not re.match(r'^\d{12}$', utr):
            messages.error(request, 'UTR must be exactly a 12-digit number.')
            return redirect('wallet:topup')
            
        # Check if UTR already exists in TopUpRequest
        if TopUpRequest.objects.filter(utr=utr).exists():
            messages.error(request, 'This UTR number has already been submitted.')
            return redirect('wallet:topup')
            
        # Create a pending TopUpRequest instead of crediting directly
        TopUpRequest.objects.create(
            user=request.user,
            utr=utr,
            amount=amount,
            coins=coins,
            status='pending'
        )
        messages.success(request, f'Payment request of ₹{amount} submitted! Admin will verify UTR: {utr} and credit your account shortly.')
        return redirect('wallet:topup')
        
    # Get user's request history
    user_requests = TopUpRequest.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, 'wallet/topup.html', {
        'page_title': 'Top Up Wallet',
        'packages': packages,
        'user_requests': user_requests
    })

@login_required
def ajax_charge_service(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})
    
    service_slug = request.POST.get('service_slug')
    service_name = request.POST.get('service_name', service_slug)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1
    
    if not service_slug:
        return JsonResponse({'status': 'error', 'message': 'Service slug is required.'})
        
    try:
        service = Service.objects.get(slug=service_slug, is_active=True)
        total_price = service.price * quantity
        if total_price > 0:
            WalletService.deduct(request.user, service_name, service.slug, total_price)
        return JsonResponse({'status': 'success', 'price': service.price, 'total_price': total_price, 'quantity': quantity})
    except Service.DoesNotExist:
        # If service not found, assume free or skip charge
        return JsonResponse({'status': 'success', 'price': 0, 'total_price': 0, 'quantity': quantity})
    except InsufficientBalanceError as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def admin_topup_requests(request):
    from django.core.exceptions import PermissionDenied
    if getattr(request.user, 'role', '') != 'admin':
        raise PermissionDenied("Only administrators can view this page.")
    
    status_filter = request.GET.get('status', 'pending')
    requests_query = TopUpRequest.objects.all().select_related('user')
    
    if status_filter != 'all':
        requests_query = requests_query.filter(status=status_filter)
        
    return render(request, 'wallet/admin_requests.html', {
        'page_title': 'Admin Top-up Requests',
        'topup_requests': requests_query,
        'current_filter': status_filter,
    })


@login_required
def admin_approve_topup(request, pk):
    from django.core.exceptions import PermissionDenied
    from django.db import transaction as db_transaction
    
    if getattr(request.user, 'role', '') != 'admin':
        raise PermissionDenied("Only administrators can approve payments.")
        
    with db_transaction.atomic():
        topup_req = get_object_or_404(TopUpRequest, pk=pk)
        if topup_req.status != 'pending':
            messages.error(request, 'This top-up request has already been processed.')
            return redirect('wallet:admin_topup_requests')
            
        # Credit the user
        WalletService.credit(
            user=topup_req.user,
            amount=topup_req.coins,
            method='qr',
            note=f"Top up via UPI (UTR: {topup_req.utr})",
            reference_id=topup_req.utr
        )
        
        # Mark as approved
        topup_req.status = 'approved'
        topup_req.save()
        
    messages.success(request, f"Approved top-up for {topup_req.user.username}. {topup_req.coins} coins credited.")
    return redirect('wallet:admin_topup_requests')


@login_required
def admin_reject_topup(request, pk):
    from django.core.exceptions import PermissionDenied
    from django.db import transaction as db_transaction
    
    if getattr(request.user, 'role', '') != 'admin':
        raise PermissionDenied("Only administrators can reject payments.")
        
    with db_transaction.atomic():
        topup_req = get_object_or_404(TopUpRequest, pk=pk)
        if topup_req.status != 'pending':
            messages.error(request, 'This top-up request has already been processed.')
            return redirect('wallet:admin_topup_requests')
            
        if request.method == 'POST':
            reason = request.POST.get('rejection_reason', '').strip()
            if not reason:
                messages.error(request, 'Rejection reason is required.')
                return redirect('wallet:admin_topup_requests')
                
            topup_req.status = 'rejected'
            topup_req.rejection_reason = reason
            topup_req.save()
            
            messages.success(request, f"Rejected top-up for {topup_req.user.username}.")
        else:
            messages.error(request, 'Invalid request method.')
        
    return redirect('wallet:admin_topup_requests')

