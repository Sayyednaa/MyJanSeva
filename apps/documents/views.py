"""Document Vault views"""
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
from django.core.paginator import Paginator
from apps.customers.models import Customer
from .models import CustomerDocument
from .forms import DocumentUploadForm


import re
from apps.id_cards.models import FarmerIDCard, RationCard

def matches_customer(card, customer):
    c_aadhaar = re.sub(r'\D', '', customer.aadhaar_number) if customer.aadhaar_number else ''
    c_mobile = re.sub(r'\D', '', customer.mobile) if customer.mobile else ''
    
    if hasattr(card, 'farmer_id'):
        card_aadhaar = re.sub(r'\D', '', card.aadhaar) if card.aadhaar else ''
        card_mobile = re.sub(r'\D', '', card.mobile) if card.mobile else ''
        if c_aadhaar and card_aadhaar and (c_aadhaar in card_aadhaar or card_aadhaar in c_aadhaar):
            return True
        if c_mobile and card_mobile and (c_mobile in card_mobile or card_mobile in c_mobile):
            return True
        if card.name_en and customer.full_name:
            if customer.full_name.lower() in card.name_en.lower() or card.name_en.lower() in customer.full_name.lower():
                return True
                
    elif hasattr(card, 'card_number'):
        card_mobile = re.sub(r'\D', '', card.mobile) if card.mobile else ''
        if c_mobile and card_mobile and (c_mobile in card_mobile or card_mobile in c_mobile):
            return True
        if card.head_of_family and customer.full_name:
            if customer.full_name.lower() in card.head_of_family.lower() or card.head_of_family.lower() in customer.full_name.lower():
                return True
        for member in card.family_members or []:
            m_name = member.get('name', '').lower()
            m_aadhaar = re.sub(r'\D', '', member.get('aadhaar', ''))
            if c_aadhaar and m_aadhaar and (c_aadhaar in m_aadhaar or m_aadhaar in c_aadhaar):
                return True
            if customer.full_name and m_name:
                if customer.full_name.lower() in m_name or m_name in customer.full_name.lower():
                    return True
                    
    return False


@login_required
def document_list(request, customer_pk=None):
    if customer_pk:
        customer = get_object_or_404(Customer, pk=customer_pk, created_by=request.user)
        docs = list(CustomerDocument.objects.filter(customer=customer).select_related('customer', 'billing_record'))
    else:
        docs = list(CustomerDocument.objects.filter(customer__created_by=request.user).select_related('customer', 'billing_record'))
        customer = None
        
    farmer_cards = FarmerIDCard.objects.filter(user=request.user)
    ration_cards = RationCard.objects.filter(user=request.user)
    
    if customer:
        matched_farmer = [fc for fc in farmer_cards if matches_customer(fc, customer)]
        matched_ration = [rc for rc in ration_cards if matches_customer(rc, customer)]
        for c in matched_farmer:
            c.customer = customer
        for c in matched_ration:
            c.customer = customer
        merged_list = docs + matched_farmer + matched_ration
    else:
        merged_list = docs + list(farmer_cards) + list(ration_cards)
        
    from django.utils.timezone import now
    def get_sort_date(item):
        return getattr(item, 'doc_date', None) or now()
        
    merged_list.sort(key=get_sort_date, reverse=True)
    
    paginator = Paginator(merged_list, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'documents/list.html', {
        'page_obj': page,
        'documents': page,
        'total': len(merged_list),
        'customer': customer,
        'page_title': f"{customer.full_name}'s Documents" if customer else 'All Documents',
    })


@login_required
def document_upload(request, customer_pk=None):
    customer = None
    if customer_pk:
        customer = get_object_or_404(Customer, pk=customer_pk, created_by=request.user)
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.uploaded_by = request.user
            if customer:
                doc.customer = customer
            doc.file_size = doc.file.size
            doc.save()
            messages.success(request, f'Document "{doc.name}" uploaded.')
            return redirect('documents:list_customer', customer_pk=doc.customer.pk)
    else:
        form = DocumentUploadForm(initial={'customer': customer})
        if customer:
            form.fields['customer'].queryset = Customer.objects.filter(pk=customer.pk)
    return render(request, 'documents/upload.html', {
        'form': form,
        'customer': customer,
        'page_title': 'Upload Document',
    })


@login_required
def document_download(request, pk):
    doc = get_object_or_404(CustomerDocument, pk=pk, customer__created_by=request.user)
    if not os.path.exists(doc.file.path):
        raise Http404("File not found.")
    return FileResponse(open(doc.file.path, 'rb'), as_attachment=True, filename=doc.name)


@login_required
def document_delete(request, pk):
    doc = get_object_or_404(CustomerDocument, pk=pk, customer__created_by=request.user)
    customer_pk = doc.customer.pk
    if request.method == 'POST':
        doc.file.delete(save=False)
        doc.delete()
        messages.success(request, 'Document deleted.')
        return redirect('documents:list_customer', customer_pk=customer_pk)
    return render(request, 'documents/confirm_delete.html', {'doc': doc})
