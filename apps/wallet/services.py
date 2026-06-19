"""Wallet service — business logic for balance management"""
from decimal import Decimal
from django.db import transaction as db_transaction
from .models import Wallet, WalletTransaction, UsageRecord


class InsufficientBalanceError(Exception):
    pass


class WalletService:

    @staticmethod
    def get_or_create_wallet(user):
        wallet, _ = Wallet.objects.get_or_create(user=user)
        return wallet

    @staticmethod
    def check_balance(user, amount):
        wallet = WalletService.get_or_create_wallet(user)
        return wallet.has_sufficient_balance(amount)

    @staticmethod
    @db_transaction.atomic
    def deduct(user, service_name, service_slug, amount, extra_data=None):
        amount = Decimal(str(amount))
        wallet = Wallet.objects.select_for_update().get(user=user)
        if not wallet.has_sufficient_balance(amount):
            raise InsufficientBalanceError(
                f"Insufficient balance. Required {amount} Coins, Available {wallet.balance} Coins"
            )
        wallet.balance -= amount
        wallet.save()

        WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type='debit',
            method='system',
            balance_after=wallet.balance,
            note=f"Service: {service_name}",
        )

        usage = UsageRecord.objects.create(
            user=user,
            service_name=service_name,
            service_slug=service_slug,
            cost=amount,
            balance_after=wallet.balance,
            extra_data=extra_data or {},
        )
        return usage

    @staticmethod
    @db_transaction.atomic
    def credit(user, amount, method='manual', note='', reference_id=''):
        amount = Decimal(str(amount))
        wallet = Wallet.objects.select_for_update().get_or_create(user=user)[0]
        wallet.balance += amount
        wallet.save()

        txn = WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type='credit',
            method=method,
            balance_after=wallet.balance,
            note=note,
            reference_id=reference_id,
        )
        return txn
