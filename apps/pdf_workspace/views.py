"""PDF Workspace views"""
import io
import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from apps.wallet.services import WalletService, InsufficientBalanceError
from apps.pricing.models import Service


def _charge(user, slug, name):
    try:
        svc = Service.objects.get(slug=slug, is_active=True)
        WalletService.deduct(user, name, slug, svc.price)
        return True, svc.price
    except Service.DoesNotExist:
        return True, 0
    except InsufficientBalanceError as e:
        return False, str(e)


@login_required
def pdf_home(request):
    return render(request, 'pdf_workspace/home.html', {'page_title': 'PDF Workspace'})

@login_required
def pdf_merge(request):
    return render(request, 'pdf_workspace/merge.html', {'page_title': 'Merge PDFs'})

@login_required
def pdf_split(request):
    return render(request, 'pdf_workspace/split.html', {'page_title': 'Split PDF'})

@login_required
def pdf_compress(request):
    return render(request, 'pdf_workspace/compress.html', {'page_title': 'Compress PDF'})

@login_required
def pdf_rotate(request):
    return render(request, 'pdf_workspace/rotate.html', {'page_title': 'Rotate PDF'})

@login_required
def image_to_pdf(request):
    return render(request, 'pdf_workspace/img_to_pdf.html', {'page_title': 'Images to PDF'})

@login_required
def pdf_password(request):
    return render(request, 'pdf_workspace/password.html', {'page_title': 'Password Protect PDF'})
