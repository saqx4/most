from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Company, Role, User
from apps.inventory.models import Product, Warehouse


class InventoryViewTestMixin:
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.role = Role.objects.create(code=Role.RoleChoices.ADMIN, name='Admin')
        self.user = User.objects.create_user(
            username='admin', password='pass1234',
            company=self.company, role=self.role, is_staff=True,
        )
        self.client.login(username='admin', password='pass1234')
        self.warehouse = Warehouse.objects.create(
            company=self.company, name='Main WH',
        )
        self.product = Product.objects.create(
            company=self.company, sku='SKU001', name='Widget',
        )


class ProductListTest(InventoryViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('inventory:product_list'))
        self.assertEqual(response.status_code, 200)


class ProductDetailTest(InventoryViewTestMixin, TestCase):
    def test_detail_200(self):
        response = self.client.get(
            reverse('inventory:product_detail', args=[self.product.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_404(self):
        response = self.client.get(
            reverse('inventory:product_detail', args=[9999])
        )
        self.assertEqual(response.status_code, 404)


class ProductCreateTest(InventoryViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('inventory:product_create'))
        self.assertEqual(response.status_code, 200)


class ProductDeleteTest(InventoryViewTestMixin, TestCase):
    def test_delete_redirects(self):
        response = self.client.post(
            reverse('inventory:product_delete', args=[self.product.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())


class StockLevelsTest(InventoryViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('inventory:stock_levels'))
        self.assertEqual(response.status_code, 200)


class StockMovementsTest(InventoryViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('inventory:stock_movements'))
        self.assertEqual(response.status_code, 200)
