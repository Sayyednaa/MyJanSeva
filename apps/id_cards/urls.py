"""ID Card URLs"""
from django.urls import path
from . import views

app_name = 'id_cards'

urlpatterns = [
    path('', views.farmer_id_workspace, name='home'),
    path('list/', views.farmer_id_list, name='farmer_list'),
    path('save/', views.save_farmer_card, name='farmer_save'),
    path('delete/', views.delete_farmer_card, name='farmer_delete'),
    path('detail/<int:pk>/', views.farmer_id_detail, name='farmer_detail'),
]
