from decimal import Decimal

from django.test import TestCase

from apps.core.models import Company
from apps.accounting.models import Currency
from apps.inventory.models import Product, Warehouse
from apps.sales.models import (
    Customer, CreditNote, SalesInvoice, SalesOrder, SalesQuote,
)


class CustomerModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.customer = Customer.objects.create(
            company=self.company, name='Acme Corp',
            email='acme@test.com',
        )

    def test_create_customer(self):
        self.assertEqual(self.customer.name, 'Acme Corp')
        self.assertTrue(self.customer.is_active)

    def test_str(self):
        self.assertEqual(str(self.customer), 'Acme Corp')


class SalesOrderModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.customer = Customer.objects.create(
            company=self.company, name='C1',
        )
        self.warehouse = Warehouse.objects.create(
            company=self.company, name='Main',
        )
        self.order = SalesOrder.objects.create(
            company=self.company, customer=self.customer,
            warehouse=self.warehouse, number='SO-0001',
        )

    def test_create_order(self):
        self.assertEqual(self.order.status, SalesOrder.Status.DRAFT)

    def test_str(self):
        self.assertEqual(str(self.order), 'SO-0001')


class SalesInvoiceModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.customer = Customer.objects.create(
            company=self.company, name='C1',
        )
        self.invoice = SalesInvoice.objects.create(
            company=self.company, customer=self.customer,
            number='INV-0001',
        )

    def test_create_invoice(self):
        self.assertEqual(self.invoice.status, SalesInvoice.Status.DRAFT)

    def test_amount_due(self):
        self.assertEqual(self.invoice.amount_due, Decimal('0'))


class SalesQuoteModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.customer = Customer.objects.create(
            company=self.company, name='C1',
        )
        self.quote = SalesQuote.objects.create(
            company=self.company, customer=self.customer,
        )

    def test_create_quote(self):
        self.assertEqual(self.quote.status, SalesQuote.Status.DRAFT)

    def test_str(self):
        self.assertEqual(str(self.quote), f'QOT#{self.quote.pk}')


class CreditNoteModelTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Co', base_currency='USD')
        self.customer = Customer.objects.create(
            company=self.company, name='C1',
        )
        self.cn = CreditNote.objects.create(
            company=self.company, customer=self.customer,
        )

    def test_create_credit_note(self):
        self.assertEqual(self.cn.status, CreditNote.Status.DRAFT)

    def test_str(self):
        self.assertEqual(str(self.cn), f'CN#{self.cn.pk}')
