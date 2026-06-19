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


@login_required
def document_list(request, customer_pk=None):
    if customer_pk:
        customer = get_object_or_404(Customer, pk=customer_pk, created_by=request.user)
        docs = CustomerDocument.objects.filter(customer=customer)
    else:
        docs = CustomerDocument.objects.filter(customer__created_by=request.user)
        customer = None
    paginator = Paginator(docs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'documents/list.html', {
        'page_obj': page,
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
