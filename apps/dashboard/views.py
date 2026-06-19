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


@login_required
def home(request):
    if request.user.is_admin:
        return admin_dashboard(request)
    return user_dashboard(request)


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

    total_revenue = WalletTransaction.objects.filter(
        transaction_type='debit'
    ).aggregate(total=Sum('amount'))['total'] or 0

    month_revenue = WalletTransaction.objects.filter(
        transaction_type='debit', created_at__date__gte=month_start
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_topups = WalletTransaction.objects.filter(
        transaction_type='credit'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Daily revenue last 14 days
    daily = WalletTransaction.objects.filter(
        transaction_type='debit',
        created_at__date__gte=today - timedelta(days=13)
    ).annotate(day=TruncDate('created_at')).values('day').annotate(
        revenue=Sum('amount')
    ).order_by('day')

    daily_labels = [(today - timedelta(days=i)).strftime('%d %b') for i in range(13, -1, -1)]
    daily_data_map = {str(d['day']): float(d['revenue']) for d in daily}
    daily_data = [daily_data_map.get(
        (today - timedelta(days=i)).strftime('%Y-%m-%d'), 0
    ) for i in range(13, -1, -1)]

    # Top services
    top_services = UsageRecord.objects.values('service_name').annotate(
        count=Count('id'), revenue=Sum('cost')
    ).order_by('-count')[:8]

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
