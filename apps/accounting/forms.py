from decimal import Decimal

from django import forms

FIELD_CLS = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none'
SELECT_CLS = 'w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none'

from apps.accounting.models import (Account, Currency, FiscalYear, JournalEntry,
    JournalLine, PaymentTerm, TaxRate)


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['code', 'name', 'type', 'parent', 'is_active', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = Account.objects.filter(company=company, is_active=True)
        self.fields['parent'].required = False


class JournalEntryForm(forms.ModelForm):
    date = forms.DateField(widget=forms.SelectDateWidget, required=True)
    lines = forms.JSONField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = JournalEntry
        fields = ['date', 'memo', 'reference', 'fiscal_year']

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        fy = kwargs.get('initial', {}).get('fiscal_year') or (self.instance.fiscal_year if getattr(self, 'instance', None) else None)
        self.fields['fiscal_year'].queryset = FiscalYear.objects.filter(company=company)
        self.fields['fiscal_year'].required = False

    def clean_lines(self):
        data = self.cleaned_data.get('lines') or []
        if not data:
            raise forms.ValidationError('Add at least one journal line.')
        accounts = [d.get('account') for d in data]
        if any(not a for a in accounts):
            raise forms.ValidationError('Each line needs an account.')
        return data


class JournalLineForm(forms.ModelForm):
    account = forms.ModelChoiceField(queryset=Account.objects.none(), widget=forms.Select(attrs={'class': 'account-select'}), required=True)

    class Meta:
        model = JournalLine
        fields = ['account', 'debit', 'credit', 'description']


# --- minimal account create/update -------------------------------------------------
class AccountCreateForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['code', 'name', 'type']

    def save(self, company=None, commit=True):
        account = super().save(commit=False)
        if company:
            account.company = company
        if commit:
            account.save()
        return account


class CurrencyForm(forms.ModelForm):
    class Meta:
        model = Currency
        fields = ['code', 'name', 'symbol', 'rate', 'is_base']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'h-4 w-4 rounded border-slate-300 text-indigo-600')
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', SELECT_CLS)
            else:
                field.widget.attrs.setdefault('class', FIELD_CLS)


class PaymentTermForm(forms.ModelForm):
    class Meta:
        model = PaymentTerm
        fields = ['name', 'net_days', 'cash_discount_days', 'cash_discount_percent']

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'h-4 w-4 rounded border-slate-300 text-indigo-600')
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', SELECT_CLS)
            else:
                field.widget.attrs.setdefault('class', FIELD_CLS)


class FiscalYearForm(forms.ModelForm):
    class Meta:
        model = FiscalYear
        fields = ['name', 'start_date', 'end_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'h-4 w-4 rounded border-slate-300 text-indigo-600')
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', SELECT_CLS)
            else:
                field.widget.attrs.setdefault('class', FIELD_CLS)