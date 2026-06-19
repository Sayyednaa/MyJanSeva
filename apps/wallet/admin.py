"""Wallet admin"""
from django.contrib import admin
from .models import Wallet, WalletTransaction, UsageRecord, TopUpRequest


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'method', 'balance_after', 'created_at')
    list_filter = ('transaction_type', 'method')
    search_fields = ('wallet__user__username', 'note')
    readonly_fields = ('created_at',)


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'service_name', 'cost', 'balance_after', 'created_at')
    list_filter = ('service_name',)
    search_fields = ('user__username', 'service_name')


@admin.register(TopUpRequest)
class TopUpRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'utr', 'amount', 'coins', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'utr')
    readonly_fields = ('created_at', 'updated_at')
