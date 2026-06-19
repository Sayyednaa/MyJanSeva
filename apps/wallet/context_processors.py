"""Wallet context processor — inject balance into every request"""
from .models import Wallet


def wallet_balance(request):
    if request.user.is_authenticated:
        try:
            balance = request.user.wallet.balance
        except Wallet.DoesNotExist:
            balance = 0
        return {'wallet_balance': balance}
    return {'wallet_balance': 0}
