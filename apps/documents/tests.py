from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.customers.models import Customer
from apps.documents.models import CustomerDocument
from apps.id_cards.models import FarmerIDCard, RationCard

User = get_user_model()

class DocumentVaultTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testoperator', password='password123')
        self.client.login(username='testoperator', password='password123')
        
        self.customer = Customer.objects.create(
            created_by=self.user,
            full_name="Rajesh Kumar",
            mobile="9988776655",
            aadhaar_number="1234 5678 9012"
        )
        
        self.doc_file = SimpleUploadedFile("test_doc.pdf", b"file_content", content_type="application/pdf")
        self.vault_doc = CustomerDocument.objects.create(
            customer=self.customer,
            uploaded_by=self.user,
            name="Rajesh Aadhaar",
            category="identity",
            doc_type="aadhaar",
            file=self.doc_file,
            file_size=1024
        )
        
        # Create Farmer ID Card matching customer
        self.farmer_card = FarmerIDCard.objects.create(
            user=self.user,
            farmer_id="F-12345",
            name_en="Rajesh Kumar",
            mobile="9988776655",
            aadhaar="1234 5678 9012"
        )
        
        # Create Ration Card matching customer via family member
        self.ration_card = RationCard.objects.create(
            user=self.user,
            card_number="R-98765",
            head_of_family="Sita Devi",
            mobile="9900112233",
            family_members=[
                {"name": "Rajesh Kumar", "aadhaar": "123456789012", "relation": "Son", "age": "30", "gender": "M", "sr": "1"}
            ]
        )
        
        # Create an unrelated Farmer ID card
        self.other_farmer_card = FarmerIDCard.objects.create(
            user=self.user,
            farmer_id="F-99999",
            name_en="Anil Singh",
            mobile="9999999999",
            aadhaar="999988887777"
        )

    def test_document_list_all_shows_all_cards(self):
        response = self.client.get(reverse('documents:list'))
        self.assertEqual(response.status_code, 200)
        docs = response.context['documents']
        # Should contain: vault_doc, farmer_card, ration_card, other_farmer_card
        self.assertEqual(len(docs), 4)
        
        # Check display properties using duck-typing
        names = [d.display_name for d in docs]
        self.assertIn("Rajesh Aadhaar", names)
        self.assertIn(self.farmer_card.display_name, names)
        self.assertIn(self.ration_card.display_name, names)
        self.assertIn(self.other_farmer_card.display_name, names)

    def test_document_list_customer_filters_matching_cards(self):
        response = self.client.get(reverse('documents:list_customer', kwargs={'customer_pk': self.customer.pk}))
        self.assertEqual(response.status_code, 200)
        docs = response.context['documents']
        # Should contain: vault_doc, farmer_card, ration_card (matched via family members), but NOT other_farmer_card
        self.assertEqual(len(docs), 3)
        
        names = [d.display_name for d in docs]
        self.assertIn("Rajesh Aadhaar", names)
        self.assertIn(self.farmer_card.display_name, names)
        self.assertIn(self.ration_card.display_name, names)
        self.assertNotIn(self.other_farmer_card.display_name, names)

    def test_customer_detail_view_merges_cards(self):
        response = self.client.get(reverse('customers:detail', kwargs={'pk': self.customer.pk}))
        self.assertEqual(response.status_code, 200)
        docs = response.context['docs']
        # Should merge up to 10 latest. Should contain the 3 matched ones.
        self.assertEqual(len(docs), 3)
        names = [d.display_name for d in docs]
        self.assertIn("Rajesh Aadhaar", names)
        self.assertIn(self.farmer_card.display_name, names)
        self.assertIn(self.ration_card.display_name, names)

    def test_delete_farmer_card_confirm_view(self):
        # GET show confirmation page
        url = reverse('id_cards:delete_farmer_card_confirm', kwargs={'pk': self.farmer_card.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.farmer_card.display_name)
        
        # POST delete the card
        response = self.client.post(url)
        self.assertRedirects(response, reverse('documents:list'))
        self.assertFalse(FarmerIDCard.objects.filter(pk=self.farmer_card.pk).exists())

    def test_delete_ration_card_confirm_view_with_customer_pk(self):
        # POST delete with customer_pk query param redirects to customer's document list
        url = reverse('id_cards:delete_ration_card_confirm', kwargs={'pk': self.ration_card.pk})
        response = self.client.post(f"{url}?customer_pk={self.customer.pk}")
        self.assertRedirects(response, reverse('documents:list_customer', kwargs={'customer_pk': self.customer.pk}))
        self.assertFalse(RationCard.objects.filter(pk=self.ration_card.pk).exists())
