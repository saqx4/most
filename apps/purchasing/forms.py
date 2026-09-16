from decimal import Decimal

from django import forms

from apps.purchasing.models import (PurchaseOrder, PurchaseOrderLine,
                                    Supplier, SupplierBill, SupplierBillLine,
                                    SupplierPayment)

FIELD_CLS = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none'


def style_form(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault('class', 'h-4 w-4 rounded border-slate-300 text-indigo-600')
        elif isinstance(field.widget, (forms.SelectDateWidget, forms.HiddenInput)):
            continue
        else:
            field.widget.attrs.setdefault('class', FIELD_CLS)


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'website', 'address',
                  'tax_id', 'currency', 'payment_term', 'ap_account', 'is_active', 'is_payable']
        widgets = {'address': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import Account, Currency, PaymentTerm
        self.fields['currency'].required = False
        self.fields['currency'].queryset = Currency.objects.all()
        self.fields['payment_term'].required = False
        self.fields['payment_term'].queryset = PaymentTerm.objects.filter(company=company)
        self.fields['ap_account'].required = False
        self.fields['ap_account'].queryset = Account.objects.filter(company=company, is_active=True)
        style_form(self)

    def save(self, company=None, commit=True):
        supplier = super().save(commit=False)
        if company:
            supplier.company = company
        if commit:
            supplier.save()
        return supplier


class POForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'order_date', 'expected_delivery', 'delivery_address', 'tax', 'currency', 'notes']
        widgets = {
            'delivery_address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import Currency, TaxRate
        self.fields['expected_delivery'].required = False
        self.fields['delivery_address'].required = False
        self.fields['tax'].required = False
        self.fields['tax'].queryset = TaxRate.objects.filter(company=company, is_active=True)
        self.fields['currency'].required = False
        self.fields['currency'].queryset = Currency.objects.all()
        self.fields['notes'].required = False
        style_form(self)

    def save(self, company=None, user=None, commit=True):
        po = super().save(commit=False)
        if company:
            po.company = company
        if user:
            po.created_by = user
        if commit:
            po.save()
        return po


class POLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent', 'tax']

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import TaxRate
        from apps.inventory.models import Product
        self.fields['product'].queryset = Product.objects.filter(company=company, is_active=True)
        self.fields['description'].required = False
        self.fields['tax'].required = False
        self.fields['tax'].queryset = TaxRate.objects.filter(company=company, is_active=True)
        style_form(self)


class BillForm(forms.ModelForm):
    class Meta:
        model = SupplierBill
        fields = ['supplier', 'order', 'bill_date', 'due_date', 'currency', 'tax', 'memo']
        widgets = {'memo': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import Currency, TaxRate
        self.fields['order'].required = False
        self.fields['order'].queryset = PurchaseOrder.objects.filter(company=company)
        self.fields['due_date'].required = False
        self.fields['currency'].required = False
        self.fields['currency'].queryset = Currency.objects.all()
        self.fields['tax'].required = False
        self.fields['tax'].queryset = TaxRate.objects.filter(company=company, is_active=True)
        self.fields['memo'].required = False
        style_form(self)

    def save(self, company=None, user=None, commit=True):
        bill = super().save(commit=False)
        if company:
            bill.company = company
        if user:
            bill.created_by = user
        if commit:
            bill.save()
        return bill


class BillLineForm(forms.ModelForm):
    class Meta:
        model = SupplierBillLine
        fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent', 'tax']

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import TaxRate
        from apps.inventory.models import Product
        self.fields['product'].queryset = Product.objects.filter(company=company, is_active=True)
        self.fields['description'].required = False
        self.fields['tax'].required = False
        self.fields['tax'].queryset = TaxRate.objects.filter(company=company, is_active=True)
        style_form(self)


class SupplierPaymentForm(forms.ModelForm):
    PAYMENT_METHODS = [
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('check', 'Check'),
        ('other', 'Other'),
    ]

    class Meta:
        model = SupplierPayment
        fields = ['supplier', 'date', 'amount', 'method', 'reference', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['method'] = forms.ChoiceField(choices=self.PAYMENT_METHODS)
        self.fields['reference'].required = False
        self.fields['notes'].required = False
        self.fields['amount'] = forms.DecimalField(min_value=Decimal('0.01'), max_digits=14, decimal_places=2)
        self.fields['supplier'].queryset = Supplier.objects.filter(company=company, is_active=True)
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