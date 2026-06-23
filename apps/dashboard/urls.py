"""Dashboard URLs"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/admin/', views.admin_dashboard, name='admin'),
    path('dashboard/admin/users/', views.admin_users, name='admin_users'),
    path('dashboard/admin/users/<int:pk>/toggle-active/', views.admin_user_toggle_active, name='admin_user_toggle_active'),
    path('dashboard/admin/users/<int:pk>/toggle-approved/', views.admin_user_toggle_approved, name='admin_user_toggle_approved'),
    path('dashboard/admin/users/<int:pk>/adjust-balance/', views.admin_user_adjust_balance, name='admin_user_adjust_balance'),
    path('help/', views.help_view, name='help'),
    path('dashboard/admin/support/', views.admin_support, name='admin_support'),
    path('dashboard/admin/support/<int:pk>/reply/', views.admin_support_reply, name='admin_support_reply'),
    path('terms/', views.terms_view, name='terms'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('todos/', views.todo_list, name='todo_list'),
    path('todos/create/', views.todo_create, name='todo_create'),
    path('todos/<int:pk>/toggle/', views.todo_toggle, name='todo_toggle'),
    path('todos/<int:pk>/delete/', views.todo_delete, name='todo_delete'),
    path('settings/', views.settings_view, name='settings'),
]
