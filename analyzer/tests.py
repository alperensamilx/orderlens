import io

import pandas as pd
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .analysis import compute_metrics, detect_column_mapping, normalize_dataframe
from .models import Dataset

ORDERS_CSV = b"""Order Date,Product,Category,Quantity,Total,Customer Email,Status
2026-04-01,Kulaklik,Elektronik,1,100,a@example.com,Tamamlandi
2026-04-02,Kulaklik,Elektronik,1,100,a@example.com,Tamamlandi
2026-04-03,Saat,Elektronik,1,200,b@example.com,Tamamlandi
2026-04-04,Ayakkabi,Giyim,1,150,c@example.com,Iptal
"""


class AnalysisUnitTests(TestCase):
    def test_detect_column_mapping_matches_common_headers(self):
        mapping = detect_column_mapping(
            ['Order Date', 'Product', 'Category', 'Quantity', 'Total', 'Customer Email', 'Status']
        )
        self.assertEqual(mapping['date'], 'Order Date')
        self.assertEqual(mapping['product'], 'Product')
        self.assertEqual(mapping['amount'], 'Total')
        self.assertEqual(mapping['quantity'], 'Quantity')
        self.assertEqual(mapping['customer'], 'Customer Email')
        self.assertEqual(mapping['category'], 'Category')
        self.assertEqual(mapping['status'], 'Status')

    def test_compute_metrics_matches_hand_calculated_values(self):
        df = pd.read_csv(io.BytesIO(ORDERS_CSV))
        mapping = detect_column_mapping(list(df.columns))
        normalized = normalize_dataframe(df, mapping)
        metrics = compute_metrics(normalized)

        self.assertEqual(metrics['order_count'], 4)
        self.assertEqual(metrics['total_revenue'], 550)
        self.assertEqual(metrics['unique_customers'], 3)
        self.assertEqual(metrics['repeat_customer_rate'], round(100 * 1 / 3, 1))
        self.assertEqual(metrics['top_products'][0]['revenue'], 200)


class AuthAndOwnershipTests(TestCase):
    def setUp(self):
        self.seller1 = User.objects.create_user(username='seller1', password='pass12345')
        self.seller2 = User.objects.create_user(username='seller2', password='pass12345')

    def test_dataset_list_requires_login(self):
        response = self.client.get(reverse('analyzer:dataset_list'))
        self.assertEqual(response.status_code, 302)

    def _upload_as(self, username, password):
        self.client.login(username=username, password=password)
        file = SimpleUploadedFile('orders.csv', ORDERS_CSV, content_type='text/csv')
        self.client.post(reverse('analyzer:dataset_list'), {'file': file})
        return Dataset.objects.latest('uploaded_at')

    def test_second_user_cannot_see_first_users_dataset(self):
        dataset = self._upload_as('seller1', 'pass12345')
        self.client.logout()

        self.client.login(username='seller2', password='pass12345')
        response = self.client.get(reverse('analyzer:analyze', args=[dataset.pk]))
        self.assertEqual(response.status_code, 404)

    def test_api_requires_authentication(self):
        response = self.client.get(reverse('analyzer:api_dataset_stats', args=[1]))
        self.assertIn(response.status_code, (401, 403))


class EndToEndFlowTests(TestCase):
    def test_register_login_upload_map_analyze_flow(self):
        response = self.client.post(reverse('analyzer:register'), {
            'username': 'newseller',
            'password1': 'ComplexPass123',
            'password2': 'ComplexPass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newseller').exists())

        response = self.client.get(reverse('analyzer:dataset_list'))
        self.assertEqual(response.status_code, 200)

        file = SimpleUploadedFile('orders.csv', ORDERS_CSV, content_type='text/csv')
        response = self.client.post(reverse('analyzer:dataset_list'), {'file': file})
        self.assertEqual(response.status_code, 302)
        dataset = Dataset.objects.latest('uploaded_at')
        self.assertEqual(dataset.owner.username, 'newseller')
        self.assertFalse(dataset.is_mapped)

        response = self.client.get(reverse('analyzer:map_columns', args=[dataset.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Order Date')

        response = self.client.post(reverse('analyzer:map_columns', args=[dataset.pk]), {
            'date': 'Order Date',
            'product': 'Product',
            'amount': 'Total',
            'quantity': 'Quantity',
            'customer': 'Customer Email',
            'category': 'Category',
            'status': 'Status',
        })
        self.assertEqual(response.status_code, 302)
        dataset.refresh_from_db()
        self.assertTrue(dataset.is_mapped)

        response = self.client.get(reverse('analyzer:analyze', args=[dataset.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Toplam Gelir')
        self.assertContains(response, '550')

        api_response = self.client.get(reverse('analyzer:api_dataset_stats', args=[dataset.pk]))
        self.assertEqual(api_response.status_code, 200)
        data = api_response.json()
        self.assertEqual(data['order_count'], 4)
        self.assertEqual(data['total_revenue'], 550)

    def test_unmapped_dataset_redirects_to_mapping(self):
        User.objects.create_user(username='seller3', password='pass12345')
        self.client.login(username='seller3', password='pass12345')
        file = SimpleUploadedFile('orders.csv', ORDERS_CSV, content_type='text/csv')
        self.client.post(reverse('analyzer:dataset_list'), {'file': file})
        dataset = Dataset.objects.latest('uploaded_at')

        response = self.client.get(reverse('analyzer:analyze', args=[dataset.pk]))
        self.assertRedirects(response, reverse('analyzer:map_columns', args=[dataset.pk]))

    def test_non_csv_upload_is_rejected(self):
        User.objects.create_user(username='seller4', password='pass12345')
        self.client.login(username='seller4', password='pass12345')
        file = SimpleUploadedFile('notes.txt', b'hello', content_type='text/plain')
        response = self.client.post(reverse('analyzer:dataset_list'), {'file': file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'csv')
