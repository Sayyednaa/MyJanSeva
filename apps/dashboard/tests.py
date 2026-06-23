from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.dashboard.models import Todo

User = get_user_model()

class TodoSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'testoperator'
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='operator@test.com',
            role='operator'
        )
        self.todo = Todo.objects.create(
            user=self.user,
            title='Test Task',
            description='Test Description',
            due_date=timezone.localdate()
        )

    def test_todo_model_creation(self):
        self.assertEqual(self.todo.title, 'Test Task')
        self.assertEqual(self.todo.description, 'Test Description')
        self.assertEqual(self.todo.due_date, timezone.localdate())
        self.assertFalse(self.todo.is_completed)
        self.assertEqual(str(self.todo), f"Test Task - {self.user.username} (Pending)")

    def test_todo_list_unauthenticated(self):
        response = self.client.get(reverse('dashboard:todo_list'))
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_todo_list_authenticated(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('dashboard:todo_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Task')

    def test_todo_create_view(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(reverse('dashboard:todo_create'), {
            'title': 'New Task',
            'description': 'New Description',
            'due_date': str(timezone.localdate())
        })
        self.assertEqual(response.status_code, 302) # Redirects back to todo_list
        self.assertTrue(Todo.objects.filter(title='New Task').exists())

    def test_todo_toggle_view(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(reverse('dashboard:todo_toggle', args=[self.todo.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['is_completed'])
        
        self.todo.refresh_from_db()
        self.assertTrue(self.todo.is_completed)

    def test_todo_delete_view(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('dashboard:todo_delete', args=[self.todo.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Todo.objects.filter(id=self.todo.id).exists())

    def test_dashboard_shows_todays_todos(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Task')


class PrintSettingsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'testoperator2'
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='operator2@test.com',
            role='operator'
        )

    def test_print_settings_model_creation(self):
        from apps.dashboard.models import PrintSettings
        settings_obj, created = PrintSettings.objects.get_or_create(user=self.user)
        self.assertTrue(created)
        self.assertEqual(settings_obj.farmer_id_width, 3.22)
        self.assertEqual(settings_obj.farmer_id_height, 2.15)
        self.assertEqual(settings_obj.ration_card_width, 3.71)
        self.assertEqual(settings_obj.ration_card_height, 2.34)
        self.assertEqual(str(settings_obj), f"Print Settings for {self.user.username}")

    def test_settings_page_unauthenticated(self):
        response = self.client.get(reverse('dashboard:settings'))
        self.assertEqual(response.status_code, 302)

    def test_settings_page_authenticated_get(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('dashboard:settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '3.22')
        self.assertContains(response, '2.15')
        self.assertContains(response, '3.71')
        self.assertContains(response, '2.34')

    def test_settings_page_post_valid(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(reverse('dashboard:settings'), {
            'farmer_id_width': '3.5',
            'farmer_id_height': '2.3',
            'ration_card_width': '4.0',
            'ration_card_height': '2.6'
        })
        self.assertEqual(response.status_code, 302) # Redirects on success
        
        from apps.dashboard.models import PrintSettings
        settings_obj = PrintSettings.objects.get(user=self.user)
        self.assertEqual(settings_obj.farmer_id_width, 3.5)
        self.assertEqual(settings_obj.farmer_id_height, 2.3)
        self.assertEqual(settings_obj.ration_card_width, 4.0)
        self.assertEqual(settings_obj.ration_card_height, 2.6)

    def test_settings_page_post_invalid(self):
        self.client.login(username=self.username, password=self.password)
        # Testing boundary values
        response = self.client.post(reverse('dashboard:settings'), {
            'farmer_id_width': '1.5', # too small, min is 2.0
            'farmer_id_height': '2.3',
            'ration_card_width': '4.0',
            'ration_card_height': '2.6'
        })
        self.assertEqual(response.status_code, 200) # Re-renders on validation error
        
        from apps.dashboard.models import PrintSettings
        settings_obj = PrintSettings.objects.get(user=self.user)
        # Should not have changed
        self.assertEqual(settings_obj.farmer_id_width, 3.22)

    def test_settings_page_reset(self):
        self.client.login(username=self.username, password=self.password)
        from apps.dashboard.models import PrintSettings
        settings_obj, created = PrintSettings.objects.get_or_create(user=self.user)
        settings_obj.farmer_id_width = 3.5
        settings_obj.save()
        
        response = self.client.post(reverse('dashboard:settings'), {
            'action': 'reset'
        })
        self.assertEqual(response.status_code, 302)
        
        settings_obj.refresh_from_db()
        self.assertEqual(settings_obj.farmer_id_width, 3.22)

