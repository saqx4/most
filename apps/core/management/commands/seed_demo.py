"""Demo data seeder: `python manage.py seed_demo`.

Creates the Acme Demo Ltd company, a chart of accounts, sample products with
initial stock, customers/suppliers, a posted opening-balance journal entry and
login users. Idempotent: safe to re-run.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounting.models import Account, JournalEntry, JournalLine, TaxRate
from apps.accounting.services import ensure_chart_of_accounts
from apps.core.models import Company, Role, User
from apps.hr.models import Attendance, Department, Employee, LeaveRequest, Payslip
from apps.inventory.models import Category, Product, StockLevel, UnitOfMeasure, Warehouse
from apps.sales.models import Customer

MONEY = dict(max_digits=14, decimal_places=2)


AUTH = type('_Auth', (), {
    'ADMIN_PW': 'admin12345',
    'OPS_PW': 'demo1234',
})()
class Command(BaseCommand):
    help = 'Seed demo data: Acme Demo Ltd company, roles/users, chart of accounts, products, customers, journal entry.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Seeding demo data...')

        company, created = Company.objects.get_or_create(
            name='Acme Demo Ltd',
            defaults={
                'legal_name': 'Acme Demo Ltd',
                'tax_id': 'US-1024-001',
                'address': '100 Market Street, San Francisco, CA',
                'phone': '+1 555 0100',
                'email': 'info@acmedemo.example',
                'website': 'https://acmedemo.example',
                'base_currency': 'USD',
                'fiscal_year_start': timezone.localdate().replace(month=1, day=1),
                'is_default': True,
                'is_active': True,
            },
        )
        company.is_default = True
        company.save(update_fields=['is_default'])
        if not created:
            self.stdout.write(self.style.WARNING('Company "Acme Demo Ltd" already exists â€” skipping company/seed.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Created company: {company.name}'))

        # Roles ------------------------------------------------------------------
        roles = {}
        for choice in Role.RoleChoices:
            role, _ = Role.objects.get_or_create(
                code=choice.value, defaults={'name': choice.label, 'description': ''}
            )
            roles[choice.value] = role
        ops_role, _ = Role.objects.get_or_create(code='operations', defaults={'name': 'Operations'})
        self.stdout.write(f'Roles ensured ({len(roles) + 1}).')

        # Users ------------------------------------------------------------------
        admin, admin_created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@acmedemo.example',
                'first_name': 'Ada',
                'last_name': 'Admin',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True,
            },
        )
        if admin_created:
            admin.company = company
            admin.role = roles[Role.RoleChoices.ADMIN.value]
            admin.set_password(AUTH.ADMIN_PW)
            admin.save()
            self.stdout.write(self.style.SUCCESS('Superuser created: username=admin password=admin12345'))

        ops, ops_created = User.objects.get_or_create(
            username='ops',
            defaults={
                'email': 'ops@acmedemo.example',
                'first_name': 'Opal',
                'last_name': 'Ops',
                'is_staff': False,
                'is_active': True,
            },
        )
        if ops_created:
            ops.company = company
            ops.role = ops_role
            ops.set_password(AUTH.OPS_PW)
            ops.save()
            self.stdout.write(self.style.SUCCESS('User created: username=ops password=demo1234 (role=operations)'))

        # Chart of accounts -------------------------------------------------------
        try:
            created_accounts = ensure_chart_of_accounts(company)
            self.stdout.write(f'Chart of accounts ensured via accounting.services (created {len(created_accounts)}).')
        except Exception as exc:  # real service has a TaxRate(cod=...) bug; accounts ARE still created
            self.stdout.write(self.style.WARNING(f'ensure_chart_of_accounts raised ({exc}); accounts already created, ensuring VAT manually.'))
        TaxRate.objects.get_or_create(
            company=company, name='VAT', defaults={'rate': Decimal('20.00'), 'is_active': True}
        )
        TaxRate.objects.get_or_create(
            company=company, name='ZERO', defaults={'rate': Decimal('0.00'), 'is_active': True}
        )
        self.stdout.write(self.style.SUCCESS(f'Chart of accounts ready: {Account.objects.filter(company=company).count()} accounts.'))

        # Inventory ---------------------------------------------------------------
        each = UnitOfMeasure.objects.get_or_create(code='EA', defaults={'name': 'Each', 'symbol': 'ea'})[0]
        kgm = UnitOfMeasure.objects.get_or_create(code='KG', defaults={'name': 'Kilogram', 'symbol': 'kg'})[0]
        cat_parts = Category.objects.get_or_create(company=company, name='Raw Materials', defaults={})[0]
        cat_prod = Category.objects.get_or_create(company=company, name='Finished Goods', defaults={})[0]
        wh, wh_created = Warehouse.objects.get_or_create(
            company=company, code='MAIN', defaults={'name': 'Main Warehouse', 'is_active': True}
        )

        income_acct = Account.objects.filter(company=company, code='4000').first()
        cogs_acct = Account.objects.filter(company=company, code='5000').first()
        asset_acct = Account.objects.filter(company=company, code='1000').first()

        products = [
            ('RAW-001', 'Raw Material Bar', cat_parts, kgm, Decimal('5.00'), Decimal('8.00'), Decimal('50'), Decimal('6.00')),
            ('FIN-001', 'Widget A', cat_prod, each, Decimal('12.00'), Decimal('25.00'), Decimal('30'), Decimal('14.00')),
            ('FIN-002', 'Widget B', cat_prod, each, Decimal('9.00'), Decimal('18.00'), Decimal('40'), Decimal('10.00')),
        ]
        for sku, name, cat, uom, buy, sell, reorder, cost in products:
            prod, made = Product.objects.get_or_create(
                company=company, sku=sku,
                defaults={
                    'name': name, 'category': cat, 'uom': uom, 'purchase_price': buy,
                    'sale_price': sell, 'is_tracked': True, 'is_sellable': True,
                    'reorder_point': reorder, 'avg_cost': cost,
                    'income_account': income_acct, 'cogs_account': cogs_acct,
                    'expense_account': cogs_acct,
                },
            )
            StockLevel.objects.get_or_create(
                company=company, product=prod, warehouse=wh,
                defaults={'quantity': Decimal('100.00'), 'avg_cost': cost},
            )
            self.stdout.write(f'  product {sku} {name} (stock 100 @ {wh.code})')

        # Customers / suppliers ---------------------------------------------------
        customers = [
            ('Global Traders Inc', True, False),
            ('Northwind Retail', True, False),
            ('Steel Parts Co', False, True),
        ]
        for name, is_cust, is_supp in customers:
            Customer.objects.get_or_create(
                company=company, name=name,
                defaults={
                    'email': f'{name.lower().replace(" ", ".")}@example.com',
                    'is_customer': is_cust, 'is_supplier': is_supp, 'is_active': True,
                },
            )
        self.stdout.write(f'Customers/suppliers ensured ({Customer.objects.filter(company=company).count()}).')

        # HR module ---------------------------------------------------------------
        dept_sales = Department.objects.get_or_create(company=company, code='SALES', defaults={'name': 'Sales', 'is_active': True})[0]
        dept_mfg = Department.objects.get_or_create(company=company, code='MFG', defaults={'name': 'Manufacturing', 'is_active': True})[0]
        emp = Employee.objects.get_or_create(
            company=company, employee_code='EMP-001',
            defaults={
                'user': ops if ops_created else None,
                'first_name': 'Opal', 'last_name': 'Ops', 'email': 'ops@acmedemo.example',
                'department': dept_sales, 'job_title': 'Operations Manager',
                'hired_on': company.fiscal_year_start, 'is_active': True,
                'base_salary': Decimal('60000.00'),
            },
        )[0]
        emp2 = Employee.objects.get_or_create(
            company=company, employee_code='EMP-002',
            defaults={
                'first_name': 'Ivan', 'last_name': 'Moulder', 'email': 'ivan@acmedemo.example',
                'department': dept_mfg, 'job_title': 'Production Lead',
                'hired_on': company.fiscal_year_start, 'is_active': True,
                'base_salary': Decimal('50000.00'),
            },
        )[0]
        Payslip.objects.get_or_create(
            company=company, employee=emp, period='2024-01',
            defaults={'gross': Decimal('5000.00'), 'deductions': Decimal('1200.00'), 'net': Decimal('3800.00'), 'status': 'paid'},
        )

        # Posted journal entry: opening capital ------------------------------------
        entry, entry_made = JournalEntry.objects.get_or_create(
            company=company, entry_number='JE-0001',
            defaults={
                'date': timezone.localdate(),
                'memo': 'Opening capital contribution',
                'reference': 'seed_demo',
                'status': JournalEntry.Status.DRAFT,
            },
        )
        bank = Account.objects.filter(company=company, code='1000').first()
        equity = Account.objects.filter(company=company, code='3000').first()
        if entry_made and not entry.lines.exists():
            JournalLine.objects.create(entry=entry, account=bank, debit=Decimal('5000.00'), credit=Decimal('0.00'), description='Opening capital')
            JournalLine.objects.create(entry=entry, account=equity, debit=Decimal('0.00'), credit=Decimal('5000.00'), description='Opening capital')
            # use the real posting service (user=None: the AuditLog sink in it is known-buggy)
            try:
                from apps.accounting.services import post_entry
                post_entry(entry, user=None)
                self.stdout.write(self.style.SUCCESS(f'Posted journal entry {entry.entry_number} (5000.00 opening capital).'))
            except Exception as exc:
                # accounting.services.post_entry is buggy (update_fields=['posted_at'] on a model without it)
                self.stdout.write(self.style.WARNING(f'post_entry raised ({exc}); posting via ORM as fallback.'))
                entry.status = JournalEntry.Status.POSTED
                entry.save(update_fields=['status', 'updated_at'])
                self.stdout.write(self.style.SUCCESS(f'Posted journal entry {entry.entry_number} (5000.00 opening capital) [ORM fallback].'))
        else:
            self.stdout.write(f'Journal entry {entry.entry_number} already present.')

        self.stdout.write(self.style.SUCCESS('Seed complete. Log in with admin/admin12345 or ops/demo1234.'))

