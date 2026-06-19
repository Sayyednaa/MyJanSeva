"""ID Card URLs"""
from django.urls import path
from . import views

app_name = 'id_cards'

urlpatterns = [
    path('', views.farmer_id_workspace, name='home'),
]
