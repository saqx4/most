from decimal import Decimal

from django import forms

from apps.sales.models import (Customer, CustomerPayment, CreditNote,
                               CreditNoteLine, PeriodicInvoice, SalesInvoice,
                               SalesInvoiceLine, SalesOrder, SalesOrderLine,
                               SalesQuote, SalesQuoteLine, SalesSettings)

FIELD_CLS = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none'
SELECT_CLS = 'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none'


def style_form(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault('class', 'h-4 w-4 rounded border-slate-300 text-indigo-600')
        elif isinstance(field.widget, (forms.SelectDateWidget, forms.HiddenInput)):
            continue
        elif isinstance(field.widget, forms.Select):
            field.widget.attrs.setdefault('class', SELECT_CLS)
        else:
            field.widget.attrs.setdefault('class', FIELD_CLS)


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'website', 'billing_address',
                  'shipping_address', 'tax_id', 'currency', 'payment_term',
                  'credit_limit', 'is_active', 'ar_account']
        widgets = {
            'billing_address': forms.Textarea(attrs={'rows': 2}),
            'shipping_address': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import Account, Currency, PaymentTerm, TaxRate
        self.fields['currency'].required = False
        self.fields['currency'].queryset = Currency.objects.all()
        self.fields['currency'].empty_label = 'Select currency (optional)'
        self.fields['payment_term'].required = False
        self.fields['payment_term'].queryset = PaymentTerm.objects.filter(company=company)
        self.fields['payment_term'].empty_label = 'Select payment term (optional)'
        self.fields['phone'].widget = forms.TextInput(attrs={
            'type': 'tel',
            'inputmode': 'tel',
            'placeholder': '+20 100 000 0000',
        })
        self.fields['ar_account'].required = False
        self.fields['ar_account'].queryset = Account.objects.filter(company=company, is_active=True)
        style_form(self)
        self._apply_translations()

    def _apply_translations(self):
        from django.utils.translation import get_language
        from apps.core.context_processors import TRANSLATIONS
        lang = get_language()
        t = TRANSLATIONS.get(lang, TRANSLATIONS.get('en', {}))
        label_map = {
            'name': t.get('NAME', 'Name'),
            'email': t.get('EMAIL', 'Email'),
            'phone': t.get('PHONE', 'Phone'),
            'website': t.get('WEBSITE', 'Website'),
            'billing_address': t.get('BILLING_ADDRESS', 'Billing Address'),
            'shipping_address': t.get('SHIPPING_ADDRESS', 'Shipping Address'),
            'tax_id': t.get('TAX_ID', 'Tax ID'),
            'currency': t.get('CURRENCY', 'Currency'),
            'payment_term': t.get('PAYMENT_TERM', 'Payment Term'),
            'credit_limit': t.get('CREDIT_LIMIT', 'Credit Limit'),
            'is_active': t.get('IS_ACTIVE', 'Is Active'),
            'ar_account': t.get('AR_ACCOUNT', 'AR Account'),
        }
        for fname, field in self.fields.items():
            if fname in label_map:
                field.label = label_map[fname]
            if hasattr(field.widget, 'choices') and field.required is False:
                field.empty_label = t.get('SELECT_AN_OPTION', 'Select an option')

    def save(self, company=None, user=None, commit=True):
        customer = super().save(commit=False)
        if company:
            customer.company = company
        if user:
            customer.created_by = user
        if commit:
            customer.save()
        return customer


class OrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = ['customer', 'warehouse', 'order_date', 'expected_delivery',
                  'currency', 'salesperson', 'tax', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import Currency, TaxRate
        from apps.core.models import User
        from apps.inventory.models import Warehouse
        self.fields['warehouse'].queryset = Warehouse.objects.filter(company=company, is_active=True)
        self.fields['expected_delivery'].required = False
        self.fields['currency'].required = False
        self.fields['currency'].queryset = Currency.objects.all()
        self.fields['salesperson'].required = False
        self.fields['salesperson'].queryset = User.objects.filter(company=company).order_by('username')
        self.fields['tax'].required = False
        self.fields['tax'].queryset = TaxRate.objects.filter(company=company, is_active=True)
        self.fields['notes'].required = False
        style_form(self)

    def save(self, company=None, user=None, commit=True):
        order = super().save(commit=False)
        if company:
            order.company = company
        if user:
            order.created_by = user
        if commit:
            order.save()
        return order


class OrderLineForm(forms.ModelForm):
    class Meta:
        model = SalesOrderLine
        fields = ['product', 'description', 'quantity', 'price', 'discount_percent', 'tax']

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import TaxRate
        from apps.inventory.models import Product
        self.fields['product'].queryset = Product.objects.filter(company=company, is_active=True, is_sellable=True)
        self.fields['description'].required = False
        self.fields['tax'].required = False
        self.fields['tax'].queryset = TaxRate.objects.filter(company=company, is_active=True)
        style_form(self)


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = SalesInvoice
        fields = ['customer', 'order', 'invoice_date', 'due_date', 'currency', 'tax', 'memo']
        widgets = {'memo': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import Currency, TaxRate
        self.fields['order'].required = False
        self.fields['order'].queryset = SalesOrder.objects.filter(company=company)
        self.fields['due_date'].required = False
        self.fields['currency'].required = False
        self.fields['currency'].queryset = Currency.objects.all()
        self.fields['tax'].required = False
        self.fields['tax'].queryset = TaxRate.objects.filter(company=company, is_active=True)
        self.fields['memo'].required = False
        style_form(self)

    def save(self, company=None, user=None, commit=True):
        invoice = super().save(commit=False)
        if company:
            invoice.company = company
        if user:
            invoice.created_by = user
        if commit:
            invoice.save()
        return invoice


class InvoiceLineForm(forms.ModelForm):
    class Meta:
        model = SalesInvoiceLine
        fields = ['product', 'description', 'quantity', 'price', 'discount_percent', 'tax']

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import TaxRate
        from apps.inventory.models import Product
        self.fields['product'].queryset = Product.objects.filter(company=company, is_active=True, is_sellable=True)
        self.fields['description'].required = False
        self.fields['tax'].required = False
        self.fields['tax'].queryset = TaxRate.objects.filter(company=company, is_active=True)
        style_form(self)


class PaymentForm(forms.ModelForm):
    PAYMENT_METHODS = [
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('check', 'Check'),
        ('other', 'Other'),
    ]

    class Meta:
        model = CustomerPayment
        fields = ['customer', 'date', 'amount', 'method', 'reference', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['method'] = forms.ChoiceField(choices=self.PAYMENT_METHODS)
        self.fields['reference'].required = False
        self.fields['notes'].required = False
        self.fields['amount'] = forms.DecimalField(min_value=Decimal('0.01'), max_digits=14, decimal_places=2)
        self.fields['customer'].queryset = Customer.objects.filter(company=company, is_active=True)
        style_form(self)

    def save(self, company=None, user=None, commit=True):
        payment = super().save(commit=False)
        if company:
            payment.company = company
        if user:
            payment.created_by = user
        if commit:
            payment.save()
        return payment


class QuoteForm(forms.ModelForm):
    class Meta:
        model = SalesQuote
        fields = ['customer', 'quote_date', 'valid_until', 'currency', 'salesperson', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import Currency
        from apps.core.models import User
        self.fields['valid_until'].required = False
        self.fields['currency'].required = False
        self.fields['currency'].queryset = Currency.objects.all()
        self.fields['salesperson'].required = False
        self.fields['salesperson'].queryset = User.objects.filter(company=company).order_by('username')
        self.fields['notes'].required = False
        style_form(self)

    def save(self, company=None, user=None, commit=True):
        quote = super().save(commit=False)
        if company:
            quote.company = company
        if user:
            quote.created_by = user
        if commit:
            quote.save()
        return quote


class QuoteLineForm(forms.ModelForm):
    class Meta:
        model = SalesQuoteLine
        fields = ['product', 'description', 'quantity', 'price', 'discount_percent']

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.inventory.models import Product
        self.fields['product'].queryset = Product.objects.filter(company=company, is_active=True, is_sellable=True)
        self.fields['description'].required = False
        style_form(self)


class CreditNoteForm(forms.ModelForm):
    class Meta:
        model = CreditNote
        fields = ['customer', 'original_invoice', 'credit_date', 'reason', 'currency']
        widgets = {'reason': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import Currency
        self.fields['original_invoice'].required = False
        self.fields['original_invoice'].queryset = SalesInvoice.objects.filter(company=company)
        self.fields['currency'].required = False
        self.fields['currency'].queryset = Currency.objects.all()
        self.fields['reason'].required = False
        style_form(self)

    def save(self, company=None, user=None, commit=True):
        cn = super().save(commit=False)
        if company:
            cn.company = company
        if user:
            cn.created_by = user
        if commit:
            cn.save()
        return cn


class CreditNoteLineForm(forms.ModelForm):
    class Meta:
        model = CreditNoteLine
        fields = ['product', 'description', 'quantity', 'price']

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.inventory.models import Product
        self.fields['product'].queryset = Product.objects.filter(company=company, is_active=True)
        self.fields['description'].required = False
        style_form(self)


class PeriodicInvoiceForm(forms.ModelForm):
    class Meta:
        model = PeriodicInvoice
        fields = ['customer', 'frequency', 'next_date', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['notes'].required = False
        style_form(self)

    def save(self, company=None, user=None, commit=True):
        periodic = super().save(commit=False)
        if company:
            periodic.company = company
        if user:
            periodic.created_by = user
        if commit:
            periodic.save()
        return periodic


class SalesSettingsForm(forms.ModelForm):
    class Meta:
        model = SalesSettings
        fields = ['default_payment_term', 'default_tax', 'invoice_prefix', 'quote_prefix',
                  'credit_note_prefix', 'order_prefix', 'default_notes', 'auto_post_invoices']
        widgets = {'default_notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import PaymentTerm, TaxRate
        self.fields['default_payment_term'].required = False
        self.fields['default_payment_term'].queryset = PaymentTerm.objects.filter(company=company)
        self.fields['default_tax'].required = False
        self.fields['default_tax'].queryset = TaxRate.objects.filter(company=company, is_active=True)
        self.fields['default_notes'].required = False
        style_form(self)