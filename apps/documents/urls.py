"""Document URLs"""
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.document_list, name='list'),
    path('customer/<int:customer_pk>/', views.document_list, name='list_customer'),
    path('upload/', views.document_upload, name='upload'),
    path('upload/<int:customer_pk>/', views.document_upload, name='upload_customer'),
    path('<int:pk>/download/', views.document_download, name='download'),
    path('<int:pk>/delete/', views.document_delete, name='delete'),
]
