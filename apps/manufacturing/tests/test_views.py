from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Company, Role, User
from apps.inventory.models import Product, Warehouse
from apps.manufacturing.models import BillOfMaterial, WorkOrder


class ManufacturingViewTestMixin:
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.role = Role.objects.create(code=Role.RoleChoices.ADMIN, name='Admin')
        self.user = User.objects.create_user(
            username='admin', password='pass1234',
            company=self.company, role=self.role, is_staff=True,
        )
        self.client.login(username='admin', password='pass1234')
        self.product = Product.objects.create(
            company=self.company, sku='FG001', name='Finished',
        )
        self.warehouse = Warehouse.objects.create(
            company=self.company, name='Main',
        )
        self.bom = BillOfMaterial.objects.create(
            company=self.company, product=self.product,
            number='BOM-001',
        )


class ManufacturingDashboardTest(ManufacturingViewTestMixin, TestCase):
    def test_dashboard_200(self):
        response = self.client.get(reverse('manufacturing:dashboard'))
        self.assertEqual(response.status_code, 200)


class BOMListTest(ManufacturingViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('manufacturing:bom_list'))
        self.assertEqual(response.status_code, 200)


class BOMDetailTest(ManufacturingViewTestMixin, TestCase):
    def test_detail_200(self):
        response = self.client.get(
            reverse('manufacturing:bom_detail', args=[self.bom.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_404(self):
        response = self.client.get(
            reverse('manufacturing:bom_detail', args=[9999])
        )
        self.assertEqual(response.status_code, 404)


class BOMCreateTest(ManufacturingViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('manufacturing:bom_create'))
        self.assertEqual(response.status_code, 200)


class BOMDeleteTest(ManufacturingViewTestMixin, TestCase):
    def test_delete_redirects(self):
        response = self.client.post(
            reverse('manufacturing:bom_delete', args=[self.bom.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(BillOfMaterial.objects.filter(pk=self.bom.pk).exists())


class WorkOrderListTest(ManufacturingViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('manufacturing:workorder_list'))
        self.assertEqual(response.status_code, 200)


class WorkOrderDetailTest(ManufacturingViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.wo = WorkOrder.objects.create(
            company=self.company, bom=self.bom,
            product=self.product, warehouse=self.warehouse,
            number='WO-0001',
        )

    def test_detail_200(self):
        response = self.client.get(
            reverse('manufacturing:workorder_detail', args=[self.wo.pk])
        )
        self.assertEqual(response.status_code, 200)


class WorkOrderCreateTest(ManufacturingViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('manufacturing:workorder_create'))
        self.assertEqual(response.status_code, 200)
