"""ID Card Studio views"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def farmer_id_workspace(request):
    return render(request, 'id_cards/farmer_workspace.html', {
        'page_title': 'Farmer ID Studio',
    })
