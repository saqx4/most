from django import forms
from django.contrib.auth.forms import UserCreationForm

from apps.core.models import Role, User

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


class UserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'role', 'is_active', 'is_staff']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-indigo-600'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-indigo-600'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = Role.objects.all()
        self.fields['role'].required = False
        self.fields['email'].required = False
        self.fields['phone'].required = False
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['is_staff'].help_text = ''
        self.fields['password1'].help_text = '<ul class="text-xs text-slate-400 mt-1 list-disc list-inside"><li>At least 8 characters.</li></ul>'
        style_form(self)
        self._apply_translations()

    def _apply_translations(self):
        from django.utils.translation import get_language
        from apps.core.context_processors import TRANSLATIONS
        lang = get_language()
        t = TRANSLATIONS.get(lang, TRANSLATIONS.get('en', {}))
        label_map = {
            'username': t.get('USERNAME', 'Username'),
            'first_name': t.get('FIRST_NAME', 'First Name'),
            'last_name': t.get('LAST_NAME', 'Last Name'),
            'email': t.get('EMAIL', 'Email'),
            'phone': t.get('PHONE', 'Phone'),
            'role': t.get('ROLE', 'Role'),
            'is_active': t.get('IS_ACTIVE', 'Is Active'),
            'is_staff': t.get('STAFF_ACCESS', 'Staff Access'),
            'password1': t.get('PASSWORD', 'Password'),
            'password2': t.get('CONFIRM_PASSWORD', 'Confirm Password'),
        }
        for fname, field in self.fields.items():
            if fname in label_map:
                field.label = label_map[fname]
            if hasattr(field.widget, 'choices') and field.required is False:
                field.empty_label = t.get('SELECT_AN_OPTION', 'Select an option')


class UserEditForm(forms.ModelForm):
    new_password = forms.CharField(
        label='New Password',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none'}),
        help_text='Leave blank to keep the current password.',
    )
    confirm_password = forms.CharField(
        label='Confirm New Password',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none'}),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'role', 'is_active', 'is_staff']
        widgets = {
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-indigo-600'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-indigo-600'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = Role.objects.all()
        self.fields['role'].required = False
        self.fields['email'].required = False
        self.fields['phone'].required = False
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['is_staff'].help_text = ''
        style_form(self)
        self._apply_translations()

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('new_password')
        confirm = cleaned.get('confirm_password')
        if pw and pw != confirm:
            self.add_error('confirm_password', 'Passwords do not match.')
        if pw and len(pw) < 8:
            self.add_error('new_password', 'Password must be at least 8 characters.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=commit)
        pw = self.cleaned_data.get('new_password')
        if pw:
            user.set_password(pw)
            if commit:
                user.save()
        return user

    def _apply_translations(self):
        from django.utils.translation import get_language
        from apps.core.context_processors import TRANSLATIONS
        lang = get_language()
        t = TRANSLATIONS.get(lang, TRANSLATIONS.get('en', {}))
        label_map = {
            'username': t.get('USERNAME', 'Username'),
            'first_name': t.get('FIRST_NAME', 'First Name'),
            'last_name': t.get('LAST_NAME', 'Last Name'),
            'email': t.get('EMAIL', 'Email'),
            'phone': t.get('PHONE', 'Phone'),
            'role': t.get('ROLE', 'Role'),
            'is_active': t.get('IS_ACTIVE', 'Is Active'),
            'is_staff': t.get('STAFF_ACCESS', 'Staff Access'),
            'new_password': t.get('NEW_PASSWORD', 'New Password'),
            'confirm_password': t.get('CONFIRM_PASSWORD', 'Confirm Password'),
        }
        for fname, field in self.fields.items():
            if fname in label_map:
                field.label = label_map[fname]
            if hasattr(field.widget, 'choices') and field.required is False:
                field.empty_label = t.get('SELECT_AN_OPTION', 'Select an option')
