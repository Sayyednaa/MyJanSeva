"""ID Card Studio views"""
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction as db_transaction
from apps.pricing.models import Service
from apps.wallet.services import WalletService, InsufficientBalanceError
from .models import FarmerIDCard, RationCard

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


@login_required
def ration_workspace(request):
    try:
        service = Service.objects.get(slug='ration-card')
        price = float(service.price)
    except Service.DoesNotExist:
        price = 50.0
        
    return render(request, 'id_cards/ration_workspace.html', {
        'page_title': 'Ration Card Studio',
        'ration_price': price,
        'wallet_balance': float(request.user.wallet.balance) if hasattr(request.user, 'wallet') else 0.0,
    })

@login_required
def ration_list(request):
    cards = RationCard.objects.filter(user=request.user)
    cards_list = []
    for card in cards:
        cards_list.append({
            'id': card.id,
            'cardNumber': card.card_number,
            'fareShopNumber': card.fare_shop_number,
            'schemeName': card.scheme_name,
            'headOfFamily': card.head_of_family,
            'address': card.address,
            'mobile': card.mobile,
            'issueDate': card.issue_date,
            'photo': card.photo,
            'familyMembers': card.family_members,
            'designStyle': card.design_style,
            'printCount': card.print_count,
            'createdAt': int(card.created_at.timestamp() * 1000)
        })
    return JsonResponse(cards_list, safe=False)

@login_required
def save_ration_card(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed.'})
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'})
    
    card_id = data.get('id')
    card_number = data.get('cardNumber', '').strip()
    fare_shop_number = data.get('fareShopNumber', '').strip()
    scheme_name = data.get('schemeName', '').strip()
    head_of_family = data.get('headOfFamily', '').strip()
    address = data.get('address', '').strip()
    mobile = data.get('mobile', '').strip()
    issue_date = data.get('issueDate', '').strip()
    photo = data.get('photo', '')
    family_members = data.get('familyMembers', [])
    design_style = data.get('designStyle', '1').strip()
    print_count = data.get('printCount', 0)

    if not card_number or not head_of_family:
        return JsonResponse({'status': 'error', 'message': 'Ration Card Number and Head of Family are required fields.'})

    try:
        with db_transaction.atomic():
            if card_id:
                try:
                    card = RationCard.objects.select_for_update().get(id=card_id, user=request.user)
                except RationCard.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Card not found or access denied.'})
            else:
                card = RationCard(user=request.user)
                # Deduct wallet first inside the transaction
                try:
                    service = Service.objects.get(slug='ration-card', is_active=True)
                    price = service.price
                    if price > 0:
                        WalletService.deduct(
                            user=request.user,
                            service_name="Ration Card Print",
                            service_slug="ration-card",
                            amount=price
                        )
                except Service.DoesNotExist:
                    pass

            card.card_number = card_number
            card.fare_shop_number = fare_shop_number
            card.scheme_name = scheme_name
            card.head_of_family = head_of_family
            card.address = address
            card.mobile = mobile
            card.issue_date = issue_date
            card.photo = photo
            card.family_members = family_members
            card.design_style = design_style
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
            'cardNumber': card.card_number,
            'fareShopNumber': card.fare_shop_number,
            'schemeName': card.scheme_name,
            'headOfFamily': card.head_of_family,
            'address': card.address,
            'mobile': card.mobile,
            'issueDate': card.issue_date,
            'photo': card.photo,
            'familyMembers': card.family_members,
            'designStyle': card.design_style,
            'printCount': card.print_count,
            'createdAt': int(card.created_at.timestamp() * 1000)
        }
    })

@login_required
def delete_ration_card(request):
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
        card = RationCard.objects.get(id=card_id, user=request.user)
        card.delete()
        return JsonResponse({'status': 'success'})
    except RationCard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Card not found or access denied.'})

@login_required
def ration_detail(request, pk):
    try:
        card = RationCard.objects.get(id=pk, user=request.user)
        return JsonResponse({
            'id': card.id,
            'cardNumber': card.card_number,
            'fareShopNumber': card.fare_shop_number,
            'schemeName': card.scheme_name,
            'headOfFamily': card.head_of_family,
            'address': card.address,
            'mobile': card.mobile,
            'issueDate': card.issue_date,
            'photo': card.photo,
            'familyMembers': card.family_members,
            'designStyle': card.design_style,
            'printCount': card.print_count,
            'createdAt': int(card.created_at.timestamp() * 1000)
        })
    except RationCard.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Card not found or access denied.'}, status=404)

