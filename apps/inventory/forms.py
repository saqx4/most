from django import forms

from apps.inventory.models import (Category, Product, StockAdjustment, StockAdjustmentLine,
                                   StockTransfer, StockTransferLine, Warehouse)

FIELD_CLS = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none'


def style_form(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault('class', 'h-4 w-4 rounded border-slate-300 text-indigo-600')
        elif isinstance(field.widget, (forms.SelectDateWidget, forms.HiddenInput)):
            continue
        else:
            field.widget.attrs.setdefault('class', FIELD_CLS)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['sku', 'name', 'category', 'uom', 'barcode', 'description',
                  'purchase_price', 'sale_price', 'income_account', 'cogs_account',
                  'expense_account', 'is_service', 'is_sellable', 'is_tracked',
                  'is_active', 'reorder_point', 'can_backorder']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounting.models import Account
        from apps.inventory.models import Category, UnitOfMeasure
        self.fields['category'].queryset = Category.objects.filter(company=company)
        self.fields['category'].required = False
        self.fields['uom'].queryset = UnitOfMeasure.objects.all()
        self.fields['uom'].required = False
        for name in ('income_account', 'cogs_account', 'expense_account'):
            self.fields[name].queryset = Account.objects.filter(company=company, is_active=True)
            self.fields[name].required = False
        style_form(self)
        self._apply_translations()

    def _apply_translations(self):
        from django.utils.translation import get_language
        from apps.core.context_processors import TRANSLATIONS
        lang = get_language()
        t = TRANSLATIONS.get(lang, TRANSLATIONS.get('en', {}))
        label_map = {
            'sku': t.get('SKU', 'SKU'),
            'name': t.get('NAME', 'Name'),
            'category': t.get('CATEGORY', 'Category'),
            'uom': t.get('UOM', 'Unit of Measure'),
            'barcode': t.get('BARCODE', 'Barcode'),
            'description': t.get('DESCRIPTION', 'Description'),
            'purchase_price': t.get('PURCHASE_PRICE', 'Purchase Price'),
            'sale_price': t.get('SALE_PRICE', 'Sale Price'),
            'income_account': t.get('INCOME_ACCOUNT', 'Income Account'),
            'cogs_account': t.get('COGS_ACCOUNT', 'COGS Account'),
            'expense_account': t.get('EXPENSE_ACCOUNT', 'Expense Account'),
            'is_service': t.get('IS_SERVICE', 'Is Service'),
            'is_sellable': t.get('IS_SELLABLE', 'Is Sellable'),
            'is_tracked': t.get('IS_TRACKED', 'Is Tracked'),
            'is_active': t.get('IS_ACTIVE', 'Is Active'),
            'reorder_point': t.get('REORDER_POINT', 'Reorder Point'),
            'can_backorder': t.get('CAN_BACKORDER', 'Can Backorder'),
        }
        for fname, field in self.fields.items():
            if fname in label_map:
                field.label = label_map[fname]
            if hasattr(field.widget, 'choices') and field.required is False:
                field.empty_label = t.get('SELECT_AN_OPTION', 'Select an option')

    def save(self, company=None, user=None, commit=True):
        product = super().save(commit=False)
        if company:
            product.company = company
        if user:
            product.created_by = user
        if commit:
            product.save()
        return product


class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['warehouse', 'date', 'reason']
        widgets = {'reason': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.inventory.models import Warehouse
        self.fields['warehouse'].queryset = Warehouse.objects.filter(company=company, is_active=True)
        self.fields['reason'].required = False
        style_form(self)


class StockAdjustmentLineForm(forms.ModelForm):
    class Meta:
        model = StockAdjustmentLine
        fields = ['product', 'quantity', 'reason']
        widgets = {'reason': forms.Textarea(attrs={'rows': 1})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.inventory.models import Product
        self.fields['product'].queryset = Product.objects.filter(company=company, is_active=True)
        self.fields['reason'].required = False
        style_form(self)


class StockTransferForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = ['from_warehouse', 'to_warehouse', 'date', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.inventory.models import Warehouse
        qs = Warehouse.objects.filter(company=company, is_active=True)
        self.fields['from_warehouse'].queryset = qs
        self.fields['to_warehouse'].queryset = qs
        self.fields['notes'].required = False
        style_form(self)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('from_warehouse') and cleaned.get('to_warehouse') \
                and cleaned['from_warehouse'].pk == cleaned['to_warehouse'].pk:
            self.add_error('to_warehouse', 'Source and destination warehouses must differ.')
        return cleaned


class StockTransferLineForm(forms.ModelForm):
    class Meta:
        model = StockTransferLine
        fields = ['product', 'quantity']

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.inventory.models import Product
        self.fields['product'].queryset = Product.objects.filter(company=company, is_active=True, is_tracked=True)
        style_form(self)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent', 'is_active']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-indigo-600'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].required = False
        self.fields['parent'].queryset = Category.objects.filter(company=company) if company else Category.objects.none()
        self.fields['parent'].empty_label = '— None —'
        style_form(self)
        self._apply_translations()

    def _apply_translations(self):
        from django.utils.translation import get_language
        from apps.core.context_processors import TRANSLATIONS
        lang = get_language()
        t = TRANSLATIONS.get(lang, TRANSLATIONS.get('en', {}))
        label_map = {
            'name': t.get('NAME', 'Name'),
            'parent': t.get('PARENT_CATEGORY', 'Parent Category'),
            'is_active': t.get('IS_ACTIVE', 'Is Active'),
        }
        for fname, field in self.fields.items():
            if fname in label_map:
                field.label = label_map[fname]
            if hasattr(field.widget, 'choices') and field.required is False:
                field.empty_label = t.get('SELECT_AN_OPTION', 'Select an option')

    def save(self, company=None, commit=True):
        cat = super().save(commit=False)
        if company:
            cat.company = company
        if commit:
            cat.save()
        return cat


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'code', 'address', 'phone', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-indigo-600'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].required = False
        self.fields['address'].required = False
        self.fields['phone'].required = False
        style_form(self)
        self._apply_translations()

    def _apply_translations(self):
        from django.utils.translation import get_language
        from apps.core.context_processors import TRANSLATIONS
        lang = get_language()
        t = TRANSLATIONS.get(lang, TRANSLATIONS.get('en', {}))
        label_map = {
            'name': t.get('NAME', 'Name'),
            'code': t.get('CODE', 'Code'),
            'address': t.get('ADDRESS', 'Address'),
            'phone': t.get('PHONE', 'Phone'),
            'is_active': t.get('IS_ACTIVE', 'Is Active'),
        }
        for fname, field in self.fields.items():
            if fname in label_map:
                field.label = label_map[fname]