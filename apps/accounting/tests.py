from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal

from apps.customers.models import Customer
from apps.documents.models import CustomerDocument
from apps.accounting.models import CustomerTransaction

User = get_user_model()

class AccountingSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'accounting_op'
        self.password = 'pass1234'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='ac@test.com',
            role='operator'
        )
        self.customer = Customer.objects.create(
            created_by=self.user,
            full_name='Aarav Sharma',
            mobile='9876543210'
        )
        # Setup dummy file for document test
        dummy_file = SimpleUploadedFile("test_doc.pdf", b"pdf_content", content_type="application/pdf")
        self.document = CustomerDocument.objects.create(
            customer=self.customer,
            uploaded_by=self.user,
            name='Aadhaar PDF',
            file=dummy_file,
            file_size=11
        )

    def test_transaction_auto_calculation_paid(self):
        # Fully paid transaction
        txn = CustomerTransaction.objects.create(
            operator=self.user,
            customer=self.customer,
            service_name='Aadhaar PVC Print',
            total_amount=Decimal('50.00'),
            paid_amount=Decimal('50.00'),
            payment_method='upi'
        )
        self.assertEqual(txn.due_amount, Decimal('0.00'))
        self.assertEqual(txn.payment_status, 'paid')

    def test_transaction_auto_calculation_debt(self):
        # Partially paid transaction (debt)
        txn = CustomerTransaction.objects.create(
            operator=self.user,
            customer=self.customer,
            service_name='Caste Certificate Print',
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('30.00'),
            payment_method='cash'
        )
        self.assertEqual(txn.due_amount, Decimal('70.00'))
        self.assertEqual(txn.payment_status, 'debt')

    def test_transaction_auto_calculation_unpaid(self):
        # Unpaid transaction
        txn = CustomerTransaction.objects.create(
            operator=self.user,
            customer=self.customer,
            service_name='Income Certificate Print',
            total_amount=Decimal('80.00'),
            paid_amount=Decimal('0.00'),
            payment_method='cash'
        )
        self.assertEqual(txn.due_amount, Decimal('80.00'))
        self.assertEqual(txn.payment_status, 'unpaid')

    def test_dashboard_unauthenticated_redirect(self):
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_authenticated_get(self):
        self.client.login(username=self.username, password=self.password)
        # Create some test transactions
        CustomerTransaction.objects.create(
            operator=self.user,
            customer=self.customer,
            service_name='Service A',
            total_amount=Decimal('150.00'),
            paid_amount=Decimal('100.00'),
            payment_method='cash'
        )
        response = self.client.get(reverse('accounting:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '₹100.00')  # Total Revenue (Paid)
        self.assertContains(response, '₹50.00')   # Outstanding Debt
        self.assertContains(response, 'Service A')

    def test_transaction_create_view(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(reverse('accounting:transaction_create'), {
            'document': self.document.pk,
            'service_name': 'PAN PVC Card',
            'total_amount': '60.00',
            'paid_amount': '10.00',
            'payment_method': 'upi',
            'notes': 'Will pay later.'
        })
        self.assertEqual(response.status_code, 302)
        txn = CustomerTransaction.objects.get(service_name='PAN PVC Card')
        self.assertEqual(txn.customer, self.customer)
        self.assertEqual(txn.document, self.document)
        self.assertEqual(txn.due_amount, Decimal('50.00'))
        self.assertEqual(txn.payment_status, 'debt')

    def test_record_payment_view(self):
        self.client.login(username=self.username, password=self.password)
        txn = CustomerTransaction.objects.create(
            operator=self.user,
            customer=self.customer,
            service_name='Merge PDF Service',
            total_amount=Decimal('40.00'),
            paid_amount=Decimal('10.00'),
            payment_method='cash'
        )
        response = self.client.post(reverse('accounting:record_payment', args=[txn.pk]), {
            'amount_paid': '30.00'
        })
        self.assertEqual(response.status_code, 302)
        txn.refresh_from_db()
        self.assertEqual(txn.paid_amount, Decimal('40.00'))
        self.assertEqual(txn.due_amount, Decimal('0.00'))
        self.assertEqual(txn.payment_status, 'paid')
