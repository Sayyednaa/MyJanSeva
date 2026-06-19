"""Photo Studio views — Pillow-powered"""
import io
import os
from PIL import Image, ImageDraw
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from apps.wallet.services import WalletService, InsufficientBalanceError
from apps.pricing.models import Service


@login_required
def photo_workspace(request):
    return render(request, 'photo_studio/workspace.html', {'page_title': 'Photo Studio Workspace'})
