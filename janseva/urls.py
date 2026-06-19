"""Jan Seva Workspace — URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.dashboard.urls', namespace='dashboard')),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('wallet/', include('apps.wallet.urls', namespace='wallet')),
    path('pricing/', include('apps.pricing.urls', namespace='pricing')),
    path('customers/', include('apps.customers.urls', namespace='customers')),
    path('documents/', include('apps.documents.urls', namespace='documents')),
    path('photo-studio/', include('apps.photo_studio.urls', namespace='photo_studio')),
    path('id-cards/', include('apps.id_cards.urls', namespace='id_cards')),
    path('pdf/', include('apps.pdf_workspace.urls', namespace='pdf_workspace')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
