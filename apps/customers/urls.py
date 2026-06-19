"""Customer URLs"""
from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.customer_list, name='list'),
    path('add/', views.customer_create, name='create'),
    path('<int:pk>/', views.customer_detail, name='detail'),
    path('<int:pk>/edit/', views.customer_edit, name='edit'),
    path('<int:pk>/delete/', views.customer_delete, name='delete'),
    path('search/', views.customer_search_ajax, name='search_ajax'),
]
