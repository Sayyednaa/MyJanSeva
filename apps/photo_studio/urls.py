"""Photo Studio URLs"""
from django.urls import path
from . import views

app_name = 'photo_studio'

urlpatterns = [
    path('', views.photo_workspace, name='workspace'),
]
