"""PDF Workspace URLs"""
from django.urls import path
from . import views

app_name = 'pdf_workspace'

urlpatterns = [
    path('', views.pdf_home, name='home'),
    path('merge/', views.pdf_merge, name='merge'),
    path('split/', views.pdf_split, name='split'),
    path('compress/', views.pdf_compress, name='compress'),
    path('rotate/', views.pdf_rotate, name='rotate'),
    path('image-to-pdf/', views.image_to_pdf, name='img_to_pdf'),
    path('password/', views.pdf_password, name='password'),
]
