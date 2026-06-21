from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.pricing.models import Service
from apps.id_cards.models import RationCard
from apps.wallet.models import Wallet

User = get_user_model()

class RationCardTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Create test operator/user
        self.user = User.objects.create_user(username='operator1', password='testpassword123')
        
        # Ensure user has a wallet and some coins
        self.wallet, _ = Wallet.objects.get_or_create(user=self.user)
        self.wallet.balance = 200.00
        self.wallet.save()
        
        # Get or create the pricing service (migrations might already have created it)
        self.service, _ = Service.objects.get_or_create(
            slug='ration-card',
            defaults={
                'name': 'Ration Card Print',
                'price': 50.00,
                'is_active': True
            }
        )
        
        # Log in
        self.client.login(username='operator1', password='testpassword123')

    def test_ration_workspace_renders(self):
        response = self.client.get(reverse('id_cards:ration_home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ration Card Studio')

    def test_ration_list_returns_json(self):
        # Create a card first
        RationCard.objects.create(
            user=self.user,
            card_number='123456789012',
            head_of_family='Babu Jalela',
            scheme_name='PHH'
        )
        response = self.client.get(reverse('id_cards:ration_list'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['cardNumber'], '123456789012')
        self.assertEqual(data[0]['headOfFamily'], 'Babu Jalela')

    def test_save_ration_card_charges_wallet(self):
        post_data = {
            'cardNumber': '987654321098',
            'schemeName': 'PHH',
            'headOfFamily': 'Babu Jalela',
            'issueDate': '23/05/2019',
            'fareShopNumber': '203453344',
            'mobile': '1234567890',
            'address': 'Gufa No 2',
            'photo': '',
            'familyMembers': []
        }
        
        # Initial wallet balance is 200.00
        self.assertEqual(self.wallet.balance, 200.00)
        
        # Save card (should charge 50.00 coins)
        response = self.client.post(
            reverse('id_cards:ration_save'),
            data=post_data,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'success')
        
        # Refetch wallet
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 150.00)
        
        # Verify card saved in database
        card = RationCard.objects.get(card_number='987654321098')
        self.assertEqual(card.head_of_family, 'Babu Jalela')
        self.assertEqual(card.user, self.user)

    def test_save_ration_card_fails_if_insufficient_funds(self):
        # Set wallet balance to low amount
        self.wallet.balance = 20.00
        self.wallet.save()
        
        post_data = {
            'cardNumber': '987654321098',
            'schemeName': 'PHH',
            'headOfFamily': 'Babu Jalela',
            'issueDate': '23/05/2019',
            'fareShopNumber': '203453344',
            'mobile': '1234567890',
            'address': 'Gufa No 2',
            'photo': '',
            'familyMembers': []
        }
        
        response = self.client.post(
            reverse('id_cards:ration_save'),
            data=post_data,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'error')
        self.assertEqual(res_data['code'], 'insufficient_balance')
        
        # Verify card was NOT saved in database
        self.assertFalse(RationCard.objects.filter(card_number='987654321098').exists())
        
        # Verify wallet balance remains unchanged
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 20.00)
