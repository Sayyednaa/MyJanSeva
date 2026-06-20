"""Dashboard views — User + Admin"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
import json

from apps.wallet.models import Wallet, WalletTransaction, UsageRecord
from apps.customers.models import Customer


def home(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            return admin_dashboard(request)
        return user_dashboard(request)
    return render(request, 'dashboard/landing.html', {
        'page_title': 'My Jan Seva — Complete Document & ID Services Platform'
    })


def terms_view(request):
    return render(request, 'dashboard/terms.html', {
        'page_title': 'Terms of Service — My Jan Seva'
    })


def privacy_view(request):
    return render(request, 'dashboard/privacy.html', {
        'page_title': 'Privacy Policy — My Jan Seva'
    })


@login_required
def user_dashboard(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    today = timezone.now().date()
    month_start = today.replace(day=1)

    today_usage = UsageRecord.objects.filter(
        user=request.user, created_at__date=today
    ).aggregate(total=Sum('cost'))['total'] or 0

    month_usage = UsageRecord.objects.filter(
        user=request.user, created_at__date__gte=month_start
    ).aggregate(total=Sum('cost'))['total'] or 0

    recent_usage = UsageRecord.objects.filter(user=request.user)[:8]
    recent_txns = WalletTransaction.objects.filter(wallet=wallet)[:5]
    customers_count = Customer.objects.filter(created_by=request.user).count()

    return render(request, 'dashboard/user.html', {
        'wallet': wallet,
        'today_usage': today_usage,
        'month_usage': month_usage,
        'recent_usage': recent_usage,
        'recent_txns': recent_txns,
        'customers_count': customers_count,
        'page_title': 'Dashboard',
    })


@login_required
def admin_dashboard(request):
    from apps.accounts.models import CustomUser
    today = timezone.now().date()
    month_start = today.replace(day=1)

    total_users = CustomUser.objects.filter(role='operator').count()

    # Convert all coin transactions to Rupees (INR) using 0.50 multiplier (2 Coins = ₹1)
    COIN_TO_INR_RATE = 0.50

    total_revenue_coins = WalletTransaction.objects.filter(
        transaction_type='debit'
    ).aggregate(total=Sum('amount'))['total'] or 0
    total_revenue = float(total_revenue_coins) * COIN_TO_INR_RATE

    month_revenue_coins = WalletTransaction.objects.filter(
        transaction_type='debit', created_at__date__gte=month_start
    ).aggregate(total=Sum('amount'))['total'] or 0
    month_revenue = float(month_revenue_coins) * COIN_TO_INR_RATE

    total_topups_coins = WalletTransaction.objects.filter(
        transaction_type='credit'
    ).aggregate(total=Sum('amount'))['total'] or 0
    total_topups = float(total_topups_coins) * COIN_TO_INR_RATE

    # Daily revenue last 14 days
    daily = WalletTransaction.objects.filter(
        transaction_type='debit',
        created_at__date__gte=today - timedelta(days=13)
    ).annotate(day=TruncDate('created_at')).values('day').annotate(
        revenue=Sum('amount')
    ).order_by('day')

    daily_labels = [(today - timedelta(days=i)).strftime('%d %b') for i in range(13, -1, -1)]
    daily_data_map = {str(d['day']): float(d['revenue']) * COIN_TO_INR_RATE for d in daily}
    daily_data = [daily_data_map.get(
        (today - timedelta(days=i)).strftime('%Y-%m-%d'), 0.0
    ) for i in range(13, -1, -1)]

    # Top services
    top_services = list(UsageRecord.objects.values('service_name').annotate(
        count=Count('id'), revenue=Sum('cost')
    ).order_by('-count')[:8])

    for s in top_services:
        if s['revenue'] is not None:
            s['revenue'] = float(s['revenue']) * COIN_TO_INR_RATE
        else:
            s['revenue'] = 0.0

    return render(request, 'dashboard/admin.html', {
        'total_users': total_users,
        'total_revenue': total_revenue,
        'month_revenue': month_revenue,
        'total_topups': total_topups,
        'daily_labels': json.dumps(daily_labels),
        'daily_data': json.dumps(daily_data),
        'top_services': top_services,
        'page_title': 'Admin Dashboard',
    })


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.db.models.functions import Coalesce
from apps.accounts.models import CustomUser

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            messages.error(request, 'Admin access required.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@admin_required
def admin_users(request):
    search_query = request.GET.get('search', '').strip()
    
    from decimal import Decimal
    # Base query for all operators
    operators = CustomUser.objects.filter(role='operator').select_related('wallet').annotate(
        total_spent=Coalesce(Sum('usage_records__cost'), Decimal('0')),
        total_usage_count=Count('usage_records__id')
    )
    
    if search_query:
        operators = operators.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(business_name__icontains=search_query)
        )
        
    operators = operators.order_by('-created_at')
    
    # Calculate operator metrics
    total_operators = operators.count()
    active_operators = operators.filter(is_active=True).count()
    
    # Wallet balances & spent calculations
    COIN_TO_INR_RATE = 0.50
    total_balance_coins = Wallet.objects.filter(user__role='operator').aggregate(total=Sum('balance'))['total'] or 0
    total_balance_inr = float(total_balance_coins) * COIN_TO_INR_RATE
    
    total_spent_coins = UsageRecord.objects.aggregate(total=Sum('cost'))['total'] or 0
    total_spent_inr = float(total_spent_coins) * COIN_TO_INR_RATE
    
    # Add rupee representations to operators list
    for op in operators:
        op.total_spent_inr = float(op.total_spent) * COIN_TO_INR_RATE
        op.wallet_balance_inr = float(op.wallet_balance) * COIN_TO_INR_RATE
        
    return render(request, 'dashboard/admin_users.html', {
        'operators': operators,
        'search_query': search_query,
        'total_operators': total_operators,
        'active_operators': active_operators,
        'total_balance_coins': total_balance_coins,
        'total_balance_inr': total_balance_inr,
        'total_spent_coins': total_spent_coins,
        'total_spent_inr': total_spent_inr,
        'page_title': 'Users & Analytics',
    })


@login_required
@admin_required
def admin_user_toggle_active(request, pk):
    user = get_object_or_404(CustomUser, pk=pk, role='operator')
    user.is_active = not user.is_active
    user.save()
    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User {user.username} has been {status}.')
    return redirect('dashboard:admin_users')


@login_required
@admin_required
def admin_user_toggle_approved(request, pk):
    user = get_object_or_404(CustomUser, pk=pk, role='operator')
    user.is_approved = not user.is_approved
    user.save()
    status = 'approved' if user.is_approved else 'disapproved'
    messages.success(request, f'User {user.username} has been {status}.')
    return redirect('dashboard:admin_users')


@login_required
@admin_required
def admin_user_adjust_balance(request, pk):
    if request.method == 'POST':
        action = request.POST.get('action')
        amount_str = request.POST.get('amount', '0')
        note = request.POST.get('note', '').strip()
        
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, 'Invalid amount.')
            return redirect('dashboard:admin_users')
            
        user = get_object_or_404(CustomUser, pk=pk, role='operator')
        from apps.wallet.services import WalletService, InsufficientBalanceError
        try:
            if action == 'credit':
                WalletService.credit(user, amount, method='manual', note=note or 'Admin balance adjustment')
                messages.success(request, f'Successfully credited {amount:.0f} Coins to {user.get_full_name() or user.username}.')
            elif action == 'deduct':
                WalletService.deduct(user, 'Manual adjustment', 'admin-adjust', amount, extra_data={'note': note})
                messages.success(request, f'Successfully deducted {amount:.0f} Coins from {user.get_full_name() or user.username}.')
        except InsufficientBalanceError:
            messages.error(request, 'Operator has insufficient balance to deduct.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            
    return redirect('dashboard:admin_users')


@login_required
def help_view(request):
    from .models import SupportTicket
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        
        if not subject or not message:
            messages.error(request, 'Subject and message are required.')
            return redirect('dashboard:help')
            
        ticket = SupportTicket.objects.create(
            user=request.user,
            subject=subject,
            message=message
        )
        
        # Send Telegram notification to admin
        try:
            from apps.wallet.utils import send_telegram_message
            full_name = request.user.get_full_name() or request.user.username
            msg = (
                f"<b>🆘 New Support Ticket #{ticket.id}</b>\n\n"
                f"• <b>User:</b> {full_name} ({request.user.email})\n"
                f"• <b>Subject:</b> {subject}\n"
                f"• <b>Message:</b>\n{message}\n"
            )
            send_telegram_message(msg)
        except Exception:
            pass
            
        messages.success(request, 'Support ticket submitted successfully! Admin will reply shortly.')
        return redirect('dashboard:help')
        
    tickets = SupportTicket.objects.filter(user=request.user)
    return render(request, 'dashboard/help.html', {
        'tickets': tickets,
        'page_title': 'Help & Support',
    })


@login_required
@admin_required
def admin_support(request):
    from .models import SupportTicket
    # Show pending tickets first, then resolved ones, ordered by newest first
    tickets = SupportTicket.objects.all().select_related('user').order_by('status', '-created_at')
    return render(request, 'dashboard/admin_support.html', {
        'tickets': tickets,
        'page_title': 'Support Tickets',
    })


@login_required
@admin_required
def admin_support_reply(request, pk):
    from .models import SupportTicket
    ticket = get_object_or_404(SupportTicket, pk=pk)
    if request.method == 'POST':
        reply = request.POST.get('reply', '').strip()
        if not reply:
            messages.error(request, 'Reply content cannot be empty.')
            return redirect('dashboard:admin_support')
            
        ticket.reply = reply
        ticket.status = 'resolved'
        ticket.save()
        messages.success(request, f'Reply sent to ticket #{ticket.id}.')
    return redirect('dashboard:admin_support')


