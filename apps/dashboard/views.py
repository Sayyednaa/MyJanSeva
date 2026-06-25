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

    # Query today's todos
    from .models import Todo
    today_todos = Todo.objects.filter(user=request.user, due_date=today)

    return render(request, 'dashboard/user.html', {
        'wallet': wallet,
        'today_usage': today_usage,
        'month_usage': month_usage,
        'recent_usage': recent_usage,
        'recent_txns': recent_txns,
        'customers_count': customers_count,
        'today_todos': today_todos,
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


from .models import Todo
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required
def todo_list(request):
    filter_type = request.GET.get('filter', 'all')
    todos = Todo.objects.filter(user=request.user)
    
    if filter_type == 'pending':
        todos = todos.filter(is_completed=False)
    elif filter_type == 'completed':
        todos = todos.filter(is_completed=True)
        
    return render(request, 'dashboard/todo_list.html', {
        'todos': todos,
        'filter_type': filter_type,
        'page_title': 'Todo Task List',
    })

@login_required
def todo_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        due_date_str = request.POST.get('due_date', '').strip()
        
        if not title:
            messages.error(request, 'Task title is required.')
            return redirect('dashboard:todo_list')
            
        due_date = None
        if due_date_str:
            try:
                due_date = timezone.datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        Todo.objects.create(
            user=request.user,
            title=title,
            description=description,
            due_date=due_date or timezone.localdate()
        )
        messages.success(request, 'Task created successfully.')
    return redirect('dashboard:todo_list')

@login_required
@require_POST
def todo_toggle(request, pk):
    todo = get_object_or_404(Todo, pk=pk, user=request.user)
    todo.is_completed = not todo.is_completed
    todo.save()
    return JsonResponse({
        'status': 'success',
        'is_completed': todo.is_completed
    })

@login_required
def todo_delete(request, pk):
    todo = get_object_or_404(Todo, pk=pk, user=request.user)
    todo.delete()
    messages.success(request, 'Task deleted successfully.')
    return redirect('dashboard:todo_list')


@login_required
def settings_view(request):
    from .models import PrintSettings
    settings_obj, created = PrintSettings.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'reset':
            settings_obj.farmer_id_width = 3.22
            settings_obj.farmer_id_height = 2.15
            settings_obj.ration_card_width = 3.71
            settings_obj.ration_card_height = 2.34
            settings_obj.save()
            messages.success(request, 'Print dimensions reset to defaults.')
            return redirect('dashboard:settings')
            
        try:
            farmer_id_width = float(request.POST.get('farmer_id_width', 3.22))
            farmer_id_height = float(request.POST.get('farmer_id_height', 2.15))
            ration_card_width = float(request.POST.get('ration_card_width', 3.71))
            ration_card_height = float(request.POST.get('ration_card_height', 2.34))
            
            # Validation limits: width [2.0, 6.0], height [1.5, 5.0]
            if not (2.0 <= farmer_id_width <= 6.0):
                raise ValueError("Farmer ID width must be between 2.0 and 6.0 inches.")
            if not (1.5 <= farmer_id_height <= 5.0):
                raise ValueError("Farmer ID height must be between 1.5 and 5.0 inches.")
            if not (2.0 <= ration_card_width <= 6.0):
                raise ValueError("Ration Card width must be between 2.0 and 6.0 inches.")
            if not (1.5 <= ration_card_height <= 5.0):
                raise ValueError("Ration Card height must be between 1.5 and 5.0 inches.")
                
            settings_obj.farmer_id_width = farmer_id_width
            settings_obj.farmer_id_height = farmer_id_height
            settings_obj.ration_card_width = ration_card_width
            settings_obj.ration_card_height = ration_card_height
            settings_obj.save()
            messages.success(request, 'Print dimensions updated successfully.')
            return redirect('dashboard:settings')
        except ValueError as e:
            messages.error(request, f'Invalid inputs: {str(e)}')
            
    return render(request, 'dashboard/settings.html', {
        'print_settings': settings_obj,
        'page_title': 'Print Settings — My Jan Seva'
    })


@login_required
@admin_required
def admin_user_detail(request, pk):
    from apps.accounts.models import CustomUser
    from apps.id_cards.models import FarmerIDCard, RationCard
    from apps.customers.models import Customer
    
    operator = get_object_or_404(CustomUser, pk=pk, role='operator')
    
    # Calculate coin balance in INR
    COIN_TO_INR_RATE = 0.50
    wallet_balance = float(operator.wallet.balance) if hasattr(operator, 'wallet') else 0.0
    wallet_balance_inr = wallet_balance * COIN_TO_INR_RATE
    
    # Get all lists
    farmer_cards = FarmerIDCard.objects.filter(user=operator).order_by('-created_at')
    ration_cards = RationCard.objects.filter(user=operator).order_by('-created_at')
    customers = Customer.objects.filter(created_by=operator).order_by('-created_at')
    
    # Calculate revenue: ₹100 per generated ID card
    farmer_count = farmer_cards.count()
    ration_count = ration_cards.count()
    total_cards = farmer_count + ration_count
    revenue_generated = total_cards * 100
    
    return render(request, 'dashboard/admin_user_detail.html', {
        'operator': operator,
        'wallet_balance': wallet_balance,
        'wallet_balance_inr': wallet_balance_inr,
        'farmer_cards': farmer_cards,
        'ration_cards': ration_cards,
        'customers': customers,
        'farmer_count': farmer_count,
        'ration_count': ration_count,
        'total_cards': total_cards,
        'revenue_generated': revenue_generated,
        'page_title': f"{operator.get_full_name() or operator.username} — Details & Operations"
    })


@login_required
@admin_required
def admin_delete_farmer_card(request, pk, card_id):
    from apps.id_cards.models import FarmerIDCard
    if request.method == 'POST':
        card = get_object_or_404(FarmerIDCard, id=card_id, user_id=pk)
        card.delete()
        messages.success(request, f"Farmer ID Card ({card.farmer_id}) deleted successfully.")
    return redirect('dashboard:admin_user_detail', pk=pk)


@login_required
@admin_required
def admin_delete_ration_card(request, pk, card_id):
    from apps.id_cards.models import RationCard
    if request.method == 'POST':
        card = get_object_or_404(RationCard, id=card_id, user_id=pk)
        card.delete()
        messages.success(request, f"Ration Card ({card.card_number}) deleted successfully.")
    return redirect('dashboard:admin_user_detail', pk=pk)


@login_required
@admin_required
def admin_delete_customer(request, pk, customer_id):
    from apps.customers.models import Customer
    if request.method == 'POST':
        customer = get_object_or_404(Customer, id=customer_id, created_by_id=pk)
        name = customer.full_name
        customer.delete()
        messages.success(request, f"Customer '{name}' deleted successfully.")
    return redirect('dashboard:admin_user_detail', pk=pk)


@login_required
@admin_required
def admin_print_farmer_card(request, pk):
    from apps.id_cards.models import FarmerIDCard
    card = get_object_or_404(FarmerIDCard, pk=pk)
    return render(request, 'dashboard/print_farmer_card.html', {'card': card})


@login_required
@admin_required
def admin_print_ration_card(request, pk):
    from apps.id_cards.models import RationCard
    card = get_object_or_404(RationCard, pk=pk)
    return render(request, 'dashboard/print_ration_card.html', {'card': card})




