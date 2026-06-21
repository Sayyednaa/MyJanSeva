"""ID Card Studio views"""
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction as db_transaction
from apps.pricing.models import Service
from apps.wallet.services import WalletService, InsufficientBalanceError
from .models import FarmerIDCard

@login_required
def farmer_id_workspace(request):
    try:
        service = Service.objects.get(slug='farmer-id')
        price = float(service.price)
    except Service.DoesNotExist:
        price = 50.0
        
    return render(request, 'id_cards/farmer_workspace.html', {
        'page_title': 'Farmer ID Studio',
        'farmer_id_price': price,
    })

@login_required
def farmer_id_list(request):
    cards = FarmerIDCard.objects.filter(user=request.user)
    cards_list = []
    for card in cards:
        cards_list.append({
            'id': card.id,
            'farmerId': card.farmer_id,
            'nameEn': card.name_en,
            'nameHi': card.name_hi,
            'dob': card.dob,
            'gender': card.gender,
            'mobile': card.mobile,
            'aadhaar': card.aadhaar,
            'address': card.address,
            'photo': card.photo,
            'landDetails': card.land_details,
            'printCount': card.print_count,
            'createdAt': int(card.created_at.timestamp() * 1000)
        })
    return JsonResponse(cards_list, safe=False)

@login_required
def save_farmer_card(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed.'})
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'})
    
    card_id = data.get('id')
    farmer_id = data.get('farmerId', '').strip()
    name_en = data.get('nameEn', '').strip()
    name_hi = data.get('nameHi', '').strip()
    dob = data.get('dob', '').strip()
    gender = data.get('gender', '').strip()
    mobile = data.get('mobile', '').strip()
    aadhaar = data.get('aadhaar', '').strip()
    address = data.get('address', '').strip()
    photo = data.get('photo', '')
    land_details = data.get('landDetails', [])
    print_count = data.get('printCount', 0)

    if not farmer_id or not name_en:
        return JsonResponse({'status': 'error', 'message': 'Farmer ID and Name (English) are required fields.'})

    try:
        with db_transaction.atomic():
            if card_id:
                try:
                    card = FarmerIDCard.objects.select_for_update().get(id=card_id, user=request.user)
                except FarmerIDCard.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Card not found or access denied.'})
            else:
                card = FarmerIDCard(user=request.user)
                # Deduct wallet first inside the transaction
                try:
                    service = Service.objects.get(slug='farmer-id', is_active=True)
                    price = service.price
                    if price > 0:
                        WalletService.deduct(
                            user=request.user,
                            service_name="Farmer ID Card Print",
                            service_slug="farmer-id",
                            amount=price
                        )
                except Service.DoesNotExist:
                    pass

            card.farmer_id = farmer_id
            card.name_en = name_en
            card.name_hi = name_hi
            card.dob = dob
            card.gender = gender
            card.mobile = mobile
            card.aadhaar = aadhaar
            card.address = address
            card.photo = photo
            card.land_details = land_details
            card.print_count = print_count
            card.save()

    except InsufficientBalanceError as e:
        return JsonResponse({
            'status': 'error',
            'code': 'insufficient_balance',
            'message': str(e),
            'redirect_url': '/wallet/topup/'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({
        'status': 'success',
        'card': {
            'id': card.id,
            'farmerId': card.farmer_id,
            'nameEn': card.name_en,
            'nameHi': card.name_hi,
            'dob': card.dob,
            'gender': card.gender,
            'mobile': card.mobile,
            'aadhaar': card.aadhaar,
            'address': card.address,
            'photo': card.photo,
            'landDetails': card.land_details,
            'printCount': card.print_count,
            'createdAt': int(card.created_at.timestamp() * 1000)
        }
    })

@login_required
def delete_farmer_card(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed.'})
    try:
        data = json.loads(request.body)
        card_id = data.get('id')
    except Exception:
        card_id = request.POST.get('id')

    if not card_id:
        return JsonResponse({'status': 'error', 'message': 'Card ID is required.'})

    try:
        card = FarmerIDCard.objects.get(id=card_id, user=request.user)
        card.delete()
        return JsonResponse({'status': 'success'})
    except FarmerIDCard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Card not found or access denied.'})

@login_required
def farmer_id_detail(request, pk):
    try:
        card = FarmerIDCard.objects.get(id=pk, user=request.user)
        return JsonResponse({
            'id': card.id,
            'farmerId': card.farmer_id,
            'nameEn': card.name_en,
            'nameHi': card.name_hi,
            'dob': card.dob,
            'gender': card.gender,
            'mobile': card.mobile,
            'aadhaar': card.aadhaar,
            'address': card.address,
            'photo': card.photo,
            'landDetails': card.land_details,
            'printCount': card.print_count,
            'createdAt': int(card.created_at.timestamp() * 1000)
        })
    except FarmerIDCard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Card not found or access denied.'}, status=404)

