from django.urls import path
from . import views

app_name = 'accounting'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('transaction/add/', views.transaction_create, name='transaction_create'),
    path('transaction/<int:pk>/edit/', views.transaction_update, name='transaction_update'),
    path('transaction/<int:pk>/pay/', views.record_payment, name='record_payment'),
    path('transaction/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
]
