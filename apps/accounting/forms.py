from django import forms
from .models import CustomerTransaction
from apps.customers.models import Customer
from apps.documents.models import CustomerDocument
from apps.id_cards.models import FarmerIDCard, RationCard
from apps.documents.views import matches_customer

class CustomerTransactionForm(forms.ModelForm):
    associated_document = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'id': 'id_document', 'class': 'form-control'})
    )
    service_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'id': 'id_service_name', 'class': 'form-control', 'placeholder': 'E.g., Aadhaar Card Print'})
    )

    class Meta:
        model = CustomerTransaction
        fields = ['service_name', 'total_amount', 'paid_amount', 'payment_method', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes...'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, user=None, customer_id=None, document_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [('', '— Select Document / Card —')]
        
        if user:
            docs = CustomerDocument.objects.filter(customer__created_by=user).select_related('customer')
            farmer_cards = FarmerIDCard.objects.filter(user=user)
            ration_cards = RationCard.objects.filter(user=user)
            
            customer = None
            if customer_id:
                customer = Customer.objects.filter(pk=customer_id, created_by=user).first()
                if customer:
                    docs = docs.filter(customer=customer)
                    farmer_cards = [fc for fc in farmer_cards if matches_customer(fc, customer)]
                    ration_cards = [rc for rc in ration_cards if matches_customer(rc, customer)]
            
            for d in docs:
                choices.append((f"doc_{d.pk}", f"{d.name} — {d.customer.full_name}"))
                
            for fc in farmer_cards:
                cust_name = "Unknown"
                if customer:
                    cust_name = customer.full_name
                else:
                    for cust in Customer.objects.filter(created_by=user):
                        if matches_customer(fc, cust):
                            cust_name = cust.full_name
                            break
                choices.append((f"farmer_{fc.pk}", f"Farmer ID: {fc.name_en} ({fc.farmer_id}) — {cust_name}"))
                
            for rc in ration_cards:
                cust_name = "Unknown"
                if customer:
                    cust_name = customer.full_name
                else:
                    for cust in Customer.objects.filter(created_by=user):
                        if matches_customer(rc, cust):
                            cust_name = cust.full_name
                            break
                choices.append((f"ration_{rc.pk}", f"Ration Card: {rc.head_of_family} ({rc.card_number}) — {cust_name}"))
                
        self.fields['associated_document'].choices = choices
        self.fields['associated_document'].required = True
        
        # In edit mode, populate initial value of associated_document from model instance
        if self.instance and self.instance.pk:
            if self.instance.document:
                self.fields['associated_document'].initial = f"doc_{self.instance.document.pk}"
            elif self.instance.farmer_card:
                self.fields['associated_document'].initial = f"farmer_{self.instance.farmer_card.pk}"
            elif self.instance.ration_card:
                self.fields['associated_document'].initial = f"ration_{self.instance.ration_card.pk}"

        if document_id:
            self.fields['associated_document'].initial = document_id

    def clean(self):
        cleaned_data = super().clean()
        doc_val = cleaned_data.get('associated_document')
        
        service_name = cleaned_data.get('service_name')
        
        if doc_val:
            parts = doc_val.split('_')
            if len(parts) == 2:
                type_name = parts[0]
                obj_id = int(parts[1])
                
                if type_name == 'doc':
                    doc = CustomerDocument.objects.filter(pk=obj_id).first()
                    if doc:
                        cleaned_data['resolved_doc'] = doc
                        cleaned_data['customer'] = doc.customer
                        if not service_name or service_name.strip() == '':
                            cleaned_data['service_name'] = doc.get_doc_type_display() or doc.name
                elif type_name == 'farmer':
                    card = FarmerIDCard.objects.filter(pk=obj_id).first()
                    if card:
                        cleaned_data['resolved_farmer'] = card
                        customer = None
                        for cust in Customer.objects.filter(created_by=card.user):
                            if matches_customer(card, cust):
                                customer = cust
                                break
                        cleaned_data['customer'] = customer
                        if not service_name or service_name.strip() == '':
                            cleaned_data['service_name'] = 'Farmer ID Card'
                elif type_name == 'ration':
                    card = RationCard.objects.filter(pk=obj_id).first()
                    if card:
                        cleaned_data['resolved_ration'] = card
                        customer = None
                        for cust in Customer.objects.filter(created_by=card.user):
                            if matches_customer(card, cust):
                                customer = cust
                                break
                        cleaned_data['customer'] = customer
                        if not service_name or service_name.strip() == '':
                            cleaned_data['service_name'] = 'Ration Card'
            
            # No customer check here since we are document-oriented
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        instance.document = None
        instance.farmer_card = None
        instance.ration_card = None
        
        if 'resolved_doc' in self.cleaned_data:
            instance.document = self.cleaned_data['resolved_doc']
        elif 'resolved_farmer' in self.cleaned_data:
            instance.farmer_card = self.cleaned_data['resolved_farmer']
        elif 'resolved_ration' in self.cleaned_data:
            instance.ration_card = self.cleaned_data['resolved_ration']
            
        if commit:
            instance.save()
        return instance
