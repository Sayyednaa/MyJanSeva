from django import forms
from .models import CustomerTransaction
from apps.customers.models import Customer
from apps.documents.models import CustomerDocument

class DocumentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} — {obj.customer.full_name}"

class CustomerTransactionForm(forms.ModelForm):
    document = DocumentChoiceField(
        queryset=CustomerDocument.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CustomerTransaction
        fields = ['document', 'service_name', 'total_amount', 'paid_amount', 'payment_method', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes...'}),
            'service_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'E.g., Aadhaar Card Print'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, user=None, customer_id=None, document_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Context-specific queryset modifications
            if customer_id:
                self.fields['document'].queryset = CustomerDocument.objects.filter(customer_id=customer_id, customer__created_by=user).select_related('customer')
            elif document_id:
                doc = CustomerDocument.objects.filter(pk=document_id, customer__created_by=user).first()
                if doc:
                    self.fields['document'].initial = doc.pk
                    self.fields['document'].queryset = CustomerDocument.objects.filter(customer_id=doc.customer_id, customer__created_by=user).select_related('customer')
                else:
                    self.fields['document'].queryset = CustomerDocument.objects.filter(customer__created_by=user).select_related('customer')
            else:
                self.fields['document'].queryset = CustomerDocument.objects.filter(customer__created_by=user).select_related('customer')
        
        self.fields['document'].empty_label = "— Select Document —"
        self.fields['document'].required = True

    def clean(self):
        cleaned_data = super().clean()
        doc = cleaned_data.get('document')
        if doc:
            cleaned_data['customer'] = doc.customer
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.customer = self.cleaned_data['customer']
        if commit:
            instance.save()
        return instance
