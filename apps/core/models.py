from django.contrib.auth.models import AbstractUser
from django.db import models


class TimeStampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CompanyScoped(TimeStampMixin):
    """Abstract base for models that belong to a company."""
    company = models.ForeignKey(
        'core.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(class)ss',
    )

    class Meta:
        abstract = True


class Company(TimeStampMixin):
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    base_currency = models.CharField(max_length=3, default='EGP')
    fiscal_year_start = models.DateField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Role(models.Model):
    class RoleChoices(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        MANAGER = 'manager', 'Manager'
        ACCOUNTANT = 'accountant', 'Accountant'
        SALES = 'sales', 'Sales'
        PURCHASING = 'purchasing', 'Purchasing'
        WAREHOUSE = 'warehouse', 'Warehouse'
        MANUFACTURING = 'manufacturing', 'Manufacturing'
        HR = 'hr', 'Human Resources'
        VIEWER = 'viewer', 'Viewer'

    code = models.CharField(max_length=20, unique=True, choices=RoleChoices.choices)
    name = models.CharField(max_length=60)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    role = models.ForeignKey(
        Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='users'
    )
    company = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='users'
    )
    phone = models.CharField(max_length=50, blank=True)

    @property
    def is_admin(self):
        return self.is_superuser or (self.role is not None and self.role.code in (
            Role.RoleChoices.ADMIN, Role.RoleChoices.MANAGER,
        ))

    @property
    def can_edit(self):
        """Admin, manager, or staff can edit any editable record."""
        return self.is_admin or self.is_staff

    def has_module_access(self, code):
        """Cheap permission gate: admin/accountant/staff pass all checks."""
        if self.is_admin or self.is_staff:
            return True
        if self.role is None:
            return False
        return self.role.code == code

    def __str__(self):
        return f'{self.get_full_name() or self.username}'


class AuditLog(TimeStampMixin):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)
    model = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} {self.action} {self.model}'


class NumberSequence(TimeStampMixin):
    """Tracks document numbers per prefix, e.g. prefix=INV padding=4 -> INV-0009."""
    name = models.CharField(max_length=60, unique=True)
    prefix = models.CharField(max_length=20)
    padding = models.PositiveSmallIntegerField(default=4)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def get_next(cls, name, prefix=None, padding=4):
        seq, _ = cls.objects.get_or_create(
            name=name, defaults={'prefix': prefix or name, 'padding': padding}
        )
        seq.last_number += 1
        seq.save(update_fields=['last_number', 'updated_at'])
        return f'{seq.prefix}-{seq.last_number:0{seq.padding}d}'


class Notification(TimeStampMixin):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title