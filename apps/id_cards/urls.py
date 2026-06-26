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
    
    path('ration/', views.ration_workspace, name='ration_home'),
    path('ration/list/', views.ration_list, name='ration_list'),
    path('ration/save/', views.save_ration_card, name='ration_save'),
    path('ration/delete/', views.delete_ration_card, name='ration_delete'),
    path('ration/detail/<int:pk>/', views.ration_detail, name='ration_detail'),
    
    # PVC Card print services
    path('print/aadhaar/', views.aadhaar_pvc, name='aadhaar_pvc'),
    path('print/pan/', views.pan_pvc, name='pan_pvc'),
    path('print/voter/', views.voter_pvc, name='voter_pvc'),
    path('print/id-card/', views.id_card_pvc, name='id_card_pvc'),
]
