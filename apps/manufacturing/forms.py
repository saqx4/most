from django import forms

from apps.manufacturing.models import BillOfMaterial, BillOfMaterialLine, WorkOrder

FIELD_CLS = 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none'


def style_form(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault('class', 'h-4 w-4 rounded border-slate-300 text-indigo-600')
        elif isinstance(field.widget, forms.HiddenInput):
            continue
        else:
            field.widget.attrs.setdefault('class', FIELD_CLS)


class BOMForm(forms.ModelForm):
    class Meta:
        model = BillOfMaterial
        fields = ['number', 'product', 'warehouse', 'quantity', 'is_active', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.inventory.models import Product, Warehouse
        self.fields['product'].queryset = Product.objects.filter(
            company=company, is_active=True
        ).order_by('name')
        self.fields['warehouse'].required = False
        self.fields['warehouse'].queryset = Warehouse.objects.filter(
            company=company, is_active=True
        )
        self.fields['notes'].required = False
        style_form(self)

    def save(self, company=None, user=None, commit=True):
        bom = super().save(commit=False)
        if company:
            bom.company = company
        if user:
            bom.created_by = user
        if commit:
            bom.save()
        return bom


class BOMLineForm(forms.ModelForm):
    class Meta:
        model = BillOfMaterialLine
        fields = ['component', 'quantity', 'uom']

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.inventory.models import Product
        self.fields['component'].queryset = Product.objects.filter(
            company=company, is_active=True
        ).order_by('name')
        self.fields['uom'].required = False
        style_form(self)


class WorkOrderForm(forms.ModelForm):
    class Meta:
        model = WorkOrder
        fields = ['bom', 'product', 'warehouse', 'quantity', 'start_date', 'due_date', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.inventory.models import Product, Warehouse
        self.fields['bom'].queryset = BillOfMaterial.objects.filter(
            company=company, is_active=True
        ).select_related('product')
        self.fields['product'].queryset = Product.objects.filter(
            company=company, is_active=True
        ).order_by('name')
        self.fields['warehouse'].queryset = Warehouse.objects.filter(
            company=company, is_active=True
        )
        self.fields['due_date'].required = False
        self.fields['notes'].required = False
        style_form(self)

    def save(self, company=None, user=None, commit=True):
        wo = super().save(commit=False)
        if company:
            wo.company = company
        if user:
            wo.created_by = user
        if commit:
            wo.save()
        return wo
