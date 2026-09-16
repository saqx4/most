from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import Company, Role, User
from apps.inventory.models import Product, Warehouse
from apps.sales.models import Customer, CreditNote, SalesInvoice, SalesOrder, SalesQuote


class SalesViewTestMixin:
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.role = Role.objects.create(code=Role.RoleChoices.ADMIN, name='Admin')
        self.user = User.objects.create_user(
            username='admin', password='pass1234',
            company=self.company, role=self.role, is_staff=True,
        )
        self.client.login(username='admin', password='pass1234')
        self.customer = Customer.objects.create(
            company=self.company, name='Acme',
        )
        self.warehouse = Warehouse.objects.create(
            company=self.company, name='Main',
        )


class CustomerListTest(SalesViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('sales:customer_list'))
        self.assertEqual(response.status_code, 200)


class CustomerDetailTest(SalesViewTestMixin, TestCase):
    def test_detail_200(self):
        response = self.client.get(
            reverse('sales:customer_detail', args=[self.customer.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_404(self):
        response = self.client.get(
            reverse('sales:customer_detail', args=[9999])
        )
        self.assertEqual(response.status_code, 404)


class CustomerCreateTest(SalesViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('sales:customer_create'))
        self.assertEqual(response.status_code, 200)


class CustomerDeleteTest(SalesViewTestMixin, TestCase):
    def test_delete_redirects(self):
        response = self.client.post(
            reverse('sales:customer_delete', args=[self.customer.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Customer.objects.filter(pk=self.customer.pk).exists())


class OrderListTest(SalesViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('sales:order_list'))
        self.assertEqual(response.status_code, 200)


class OrderDetailTest(SalesViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.order = SalesOrder.objects.create(
            company=self.company, customer=self.customer,
            warehouse=self.warehouse, number='SO-0001',
        )

    def test_detail_200(self):
        response = self.client.get(
            reverse('sales:order_detail', args=[self.order.pk])
        )
        self.assertEqual(response.status_code, 200)


class OrderCreateTest(SalesViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('sales:order_create'))
        self.assertEqual(response.status_code, 200)


class InvoiceListTest(SalesViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('sales:invoice_list'))
        self.assertEqual(response.status_code, 200)


class InvoiceDetailTest(SalesViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.invoice = SalesInvoice.objects.create(
            company=self.company, customer=self.customer,
            number='INV-0001',
        )

    def test_detail_200(self):
        response = self.client.get(
            reverse('sales:invoice_detail', args=[self.invoice.pk])
        )
        self.assertEqual(response.status_code, 200)


class InvoiceCreateTest(SalesViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('sales:invoice_create'))
        self.assertEqual(response.status_code, 200)


class QuoteListTest(SalesViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('sales:quote_list'))
        self.assertEqual(response.status_code, 200)


class QuoteDetailTest(SalesViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.quote = SalesQuote.objects.create(
            company=self.company, customer=self.customer,
        )

    def test_detail_200(self):
        response = self.client.get(
            reverse('sales:quote_detail', args=[self.quote.pk])
        )
        self.assertEqual(response.status_code, 200)


class QuoteCreateTest(SalesViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('sales:quote_create'))
        self.assertEqual(response.status_code, 200)


class CreditNoteListTest(SalesViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('sales:creditnote_list'))
        self.assertEqual(response.status_code, 200)


class CreditNoteDetailTest(SalesViewTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cn = CreditNote.objects.create(
            company=self.company, customer=self.customer,
        )

    def test_detail_200(self):
        response = self.client.get(
            reverse('sales:creditnote_detail', args=[self.cn.pk])
        )
        self.assertEqual(response.status_code, 200)


class CreditNoteCreateTest(SalesViewTestMixin, TestCase):
    def test_create_page_200(self):
        response = self.client.get(reverse('sales:creditnote_create'))
        self.assertEqual(response.status_code, 200)


class PaymentListTest(SalesViewTestMixin, TestCase):
    def test_list_200(self):
        response = self.client.get(reverse('sales:payment_list'))
        self.assertEqual(response.status_code, 200)


class BillingManagementTest(SalesViewTestMixin, TestCase):
    def test_page_200(self):
        response = self.client.get(reverse('sales:billing_management'))
        self.assertEqual(response.status_code, 200)
