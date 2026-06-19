"""Document forms"""
from django import forms
from apps.customers.models import Customer
from .models import CustomerDocument


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = CustomerDocument
        fields = ['customer', 'category', 'doc_type', 'name', 'file', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
