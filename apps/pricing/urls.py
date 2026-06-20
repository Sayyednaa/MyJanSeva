"""Pricing URLs"""
from django.urls import path
from . import views

app_name = 'pricing'

urlpatterns = [
    path('', views.service_list, name='list'),
    path('view/', views.user_service_list, name='view_pricing'),
    path('add/', views.service_create, name='create'),
    path('<int:pk>/edit/', views.service_edit, name='edit'),
    path('<int:pk>/toggle/', views.service_toggle, name='toggle'),
]
