from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_manager_role'),
        ('accounting', '0001_initial'),
        ('inventory', '0001_initial'),
        ('sales', '0001_initial'),
        ('purchasing', '0001_initial'),
        ('manufacturing', '0001_initial'),
        ('hr', '0001_initial'),
    ]

    operations = [
        # User lookups
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_user_role ON core_user(role_id);",
            "DROP INDEX IF EXISTS idx_user_role;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_user_active ON core_user(is_active);",
            "DROP INDEX IF EXISTS idx_user_active;",
        ),
        # Accounting
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_journal_line_account ON accounting_journalline(account_id);",
            "DROP INDEX IF EXISTS idx_journal_line_account;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_journal_entry_date ON accounting_journalentry(date);",
            "DROP INDEX IF EXISTS idx_journal_entry_date;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_journal_entry_status ON accounting_journalentry(status);",
            "DROP INDEX IF EXISTS idx_journal_entry_status;",
        ),
        # Inventory
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_product_sku ON inventory_product(sku);",
            "DROP INDEX IF EXISTS idx_product_sku;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_product_company ON inventory_product(company_id);",
            "DROP INDEX IF EXISTS idx_product_company;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_stock_level_product ON inventory_stocklevel(product_id);",
            "DROP INDEX IF EXISTS idx_stock_level_product;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_stock_level_warehouse ON inventory_stocklevel(warehouse_id);",
            "DROP INDEX IF EXISTS idx_stock_level_warehouse;",
        ),
        # Sales
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_invoice_customer ON sales_salesinvoice(customer_id);",
            "DROP INDEX IF EXISTS idx_invoice_customer;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_invoice_status ON sales_salesinvoice(status);",
            "DROP INDEX IF EXISTS idx_invoice_status;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_invoice_date ON sales_salesinvoice(invoice_date);",
            "DROP INDEX IF EXISTS idx_invoice_date;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_invoice_due_date ON sales_salesinvoice(due_date);",
            "DROP INDEX IF EXISTS idx_invoice_due_date;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_customer_company ON sales_customer(company_id);",
            "DROP INDEX IF EXISTS idx_customer_company;",
        ),
        # Purchasing
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_po_supplier ON purchasing_purchaseorder(supplier_id);",
            "DROP INDEX IF EXISTS idx_po_supplier;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_po_status ON purchasing_purchaseorder(status);",
            "DROP INDEX IF EXISTS idx_po_status;",
        ),
        # Manufacturing
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_wo_status ON manufacturing_workorder(status);",
            "DROP INDEX IF EXISTS idx_wo_status;",
        ),
        # HR
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_employee_company ON hr_employee(company_id);",
            "DROP INDEX IF EXISTS idx_employee_company;",
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_payslip_employee ON hr_payslip(employee_id);",
            "DROP INDEX IF EXISTS idx_payslip_employee;",
        ),
    ]
