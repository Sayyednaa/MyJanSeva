"""Wallet URLs"""
from django.urls import path
from . import views

app_name = 'wallet'

urlpatterns = [
    path('', views.wallet_dashboard, name='dashboard'),
    path('topup/', views.topup_view, name='topup'),
    path('transactions/', views.transaction_history, name='transactions'),
    path('usage/', views.usage_history, name='usage'),
    path('ajax-charge/', views.ajax_charge_service, name='ajax_charge'),
    path('admin/topups/', views.admin_topup_requests, name='admin_topup_requests'),
    path('admin/topups/<int:pk>/approve/', views.admin_approve_topup, name='admin_approve_topup'),
    path('admin/topups/<int:pk>/reject/', views.admin_reject_topup, name='admin_reject_topup'),
]
