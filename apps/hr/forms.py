from django import forms

from apps.core.models import User
from apps.hr.models import Department, Employee, Payslip


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'employee_code', 'user', 'first_name', 'last_name', 'email', 'phone',
            'department', 'job_title', 'hired_on', 'is_active', 'base_salary',
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'input'}),
            'hired_on': forms.DateInput(attrs={'type': 'date', 'class': 'input'}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self.fields['user'].queryset = User.objects.filter(company=company) if company else User.objects.none()
        self.fields['user'].required = False
        self.fields['department'].queryset = Department.objects.filter(company=company) if company else Department.objects.none()
        self.fields['department'].required = False
        self._apply_translations()

    def _apply_translations(self):
        from django.utils.translation import get_language
        from apps.core.context_processors import TRANSLATIONS
        lang = get_language()
        t = TRANSLATIONS.get(lang, TRANSLATIONS.get('en', {}))
        label_map = {
            'employee_code': t.get('EMPLOYEE_CODE', 'Employee Code'),
            'user': t.get('USER', 'User'),
            'first_name': t.get('FIRST_NAME', 'First Name'),
            'last_name': t.get('LAST_NAME', 'Last Name'),
            'email': t.get('EMAIL', 'Email'),
            'phone': t.get('PHONE', 'Phone'),
            'department': t.get('DEPARTMENT', 'Department'),
            'job_title': t.get('JOB_TITLE', 'Job Title'),
            'hired_on': t.get('HIRED_ON', 'Hired On'),
            'is_active': t.get('IS_ACTIVE', 'Is Active'),
            'base_salary': t.get('BASE_SALARY', 'Base Salary'),
        }
        for fname, field in self.fields.items():
            if fname in label_map:
                field.label = label_map[fname]
            if hasattr(field.widget, 'choices') and field.required is False:
                field.empty_label = t.get('SELECT_AN_OPTION', 'Select an option')

    def save(self, commit=True):
        employee = super().save(commit=False)
        if self.company:
            employee.company = self.company
        if commit:
            employee.save()
        return employee


class PayslipForm(forms.ModelForm):
    class Meta:
        model = Payslip
        fields = ['employee', 'period', 'gross', 'deductions', 'net', 'status', 'issued_on', 'notes']
        widgets = {
            'period': forms.TextInput(attrs={'placeholder': 'YYYY-MM'}),
            'issued_on': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        self.fields['employee'].queryset = Employee.objects.filter(company=company).order_by('employee_code')
        self._apply_translations()

    def _apply_translations(self):
        from django.utils.translation import get_language
        from apps.core.context_processors import TRANSLATIONS
        lang = get_language()
        t = TRANSLATIONS.get(lang, TRANSLATIONS.get('en', {}))
        label_map = {
            'employee': t.get('EMPLOYEE', 'Employee'),
            'period': t.get('PERIOD', 'Period'),
            'gross': t.get('GROSS', 'Gross'),
            'deductions': t.get('DEDUCTIONS', 'Deductions'),
            'net': t.get('NET', 'Net'),
            'status': t.get('STATUS', 'Status'),
            'issued_on': t.get('ISSUED_ON', 'Issued On'),
            'notes': t.get('NOTES', 'Notes'),
        }
        for fname, field in self.fields.items():
            if fname in label_map:
                field.label = label_map[fname]
            if hasattr(field.widget, 'choices') and field.required is False:
                field.empty_label = t.get('SELECT_AN_OPTION', 'Select an option')

    def clean(self):
        cleaned = super().clean()
        gross = cleaned.get('gross') or 0
        deductions = cleaned.get('deductions') or 0
        net = cleaned.get('net')
        if cleaned.get('gross') is None and cleaned.get('deductions') is not None:
            cleaned['net'] = gross - deductions
        return cleaned

    def save(self, commit=True):
        payslip = super().save(commit=False)
        if self.company:
            payslip.company = self.company
        if payslip.net is None:
            payslip.net = (payslip.gross or 0) - (payslip.deductions or 0)
        if commit:
            payslip.save()
        return payslip


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.core.context_processors import TRANSLATIONS
        from django.utils.translation import get_language
        lang = get_language()
        t = TRANSLATIONS.get(lang, TRANSLATIONS.get('en', {}))
        self.fields['name'].label = t.get('NAME', 'Name')
        self.fields['name'].widget.attrs.setdefault('class', 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none')