# Daftra vs Your ERP — Full Gap Analysis
Generated from 299 scraped Daftra pages vs existing codebase.

---

## Legend
- ✅ Exists in your ERP (model + view)
- ⚠️ Partially exists (model exists but missing fields/views/features)
- ❌ Missing entirely

---

## 1. SALES MODULE (المبيعات)

### Invoices (الفواتير)
| Feature | Status | Notes |
|---|---|---|
| Invoice list with filters | ⚠️ | Views exist but missing filter by: status, date range, client, branch |
| Create invoice | ⚠️ | Missing: shipping, discount per line, multi-tax, order ref |
| Invoice status flow (Draft→Confirmed→Paid→Void) | ✅ | |
| Invoice PDF / print | ⚠️ | pdf.py exists, missing template designs |
| Send invoice by email | ❌ | No email sending on invoices |
| Invoice payment recording | ⚠️ | Basic exists, missing: partial payments, payment method |
| Recurring invoices (الفواتير الدورية) | ❌ | No subscription/recurring model |
| Credit notes (إشعارات دائنة) | ❌ | No credit note model |
| Sales returns (الفواتير المرتجعة) | ❌ | No sales return model |
| Sales orders / order release (إصدار أوامر البيع) | ❌ | No sales order model |
| Invoice templates / designs | ❌ | No invoice layout system |
| Import invoices (CSV) | ❌ | |

### Quotes (عروض الأسعار)
| Feature | Status | Notes |
|---|---|---|
| Quote list | ❌ | No quote model |
| Create quote | ❌ | Fields: client, date, expiry, items, discount, tax, notes, terms |
| Convert quote to invoice | ❌ | |
| Quote settings (numbering, expiry default) | ❌ | |
| View/share quote (public link) | ❌ | |

### Sales Commissions (المبيعات المستهدفة والعمولات)
| Feature | Status | Notes |
|---|---|---|
| Commission rules | ❌ | Fields: name, type (percent/fixed), target, employee |
| Sales periods / commission sheets | ❌ | |
| Commission dashboard | ❌ | |

### Sales Settings (إعدادات المبيعات)
| Feature | Status | Notes |
|---|---|---|
| Default payment terms | ❌ | |
| Default tax | ❌ | |
| Shipping & delivery settings | ❌ | |
| Invoice numbering settings | ⚠️ | NumberSequence exists but no UI |

---

## 2. PURCHASING MODULE (المشتريات)

### Purchase Requests (طلبات الشراء)
| Feature | Status | Notes |
|---|---|---|
| Purchase request list | ❌ | No model |
| Create purchase request | ❌ | Fields: item, qty, reason, requested by, date |

### Purchase Quotation Requests (طلبات عروض الأسعار)
| Feature | Status | Notes |
|---|---|---|
| RFQ list | ❌ | No model |
| Create RFQ | ❌ | Fields: supplier, items, date, notes |

### Purchase Quotations (عروض أسعار المشتريات)
| Feature | Status | Notes |
|---|---|---|
| Quotation list | ❌ | No model |
| Create/compare quotations | ❌ | |

### Purchase Orders (أوامر الشراء)
| Feature | Status | Notes |
|---|---|---|
| PO list | ✅ | |
| Create PO | ✅ | |
| PO status flow | ✅ | |
| Missing PO fields | ⚠️ | Missing: branch, shipping address per PO, approved by |

### Purchase Invoices / Bills (فواتير الشراء)
| Feature | Status | Notes |
|---|---|---|
| Bill list | ✅ | SupplierBill |
| Create bill | ✅ | |
| Bill payments | ✅ | SupplierPayment + APPaymentAllocation |
| Missing fields | ⚠️ | Missing: debit note (إشعار مدين), purchase return model |

### Purchase Returns (مرتجعات المشتريات)
| Feature | Status | Notes |
|---|---|---|
| Return list | ❌ | No model |
| Create purchase return | ❌ | Fields: supplier, original bill ref, items, qty, reason |

### Debit Notes (إشعارات مدينة)
| Feature | Status | Notes |
|---|---|---|
| Debit note list | ❌ | No model |
| Create debit note | ❌ | |

### Suppliers (الموردين)
| Feature | Status | Notes |
|---|---|---|
| Supplier list | ✅ | |
| Add/edit supplier | ✅ | |
| Missing fields | ⚠️ | Missing: opening balance, credit limit, bank details, attachment |
| Import suppliers (CSV) | ❌ | |

### Purchasing Settings
| Feature | Status | Notes |
|---|---|---|
| Default account per document type | ❌ | |
| Numbering settings | ⚠️ | No UI |

---

## 3. INVENTORY MODULE (المخزون)

### Products & Services (المنتجات والخدمات)
| Feature | Status | Notes |
|---|---|---|
| Product list with tabs (All/Product/Service/Raw) | ⚠️ | List exists, missing tab filters |
| Add product | ✅ | |
| Add service | ⚠️ | is_service flag exists, no separate form |
| Product detail page (stock by warehouse, movements) | ⚠️ | Basic exists |
| Product images | ❌ | No image field |
| Product brands (العلامات التجارية) | ❌ | No brand model |
| Unit templates (وحدات القياس) | ⚠️ | UnitOfMeasure exists, no UI for unit groups |
| Price lists (قوائم الأسعار) | ❌ | No price list model |
| Import products (CSV) | ❌ | |
| Barcode support | ⚠️ | Field exists, no scan UI |

### Warehouses (المستودعات)
| Feature | Status | Notes |
|---|---|---|
| Warehouse list | ✅ | |
| Add/edit warehouse | ✅ | |
| Warehouse permissions (per role/employee/branch) | ❌ | Daftra has per-warehouse view/create/edit permissions |
| Link warehouse to accounting account | ❌ | |

### Stock Vouchers / Movements (الأذون المخزنية)
| Feature | Status | Notes |
|---|---|---|
| Movement types: IN/OUT/TRANSFER/ADJUST | ✅ | StockMovement model |
| Stock voucher form (إضافة إذن مخزني) | ⚠️ | StockAdjustment exists, missing IN/OUT voucher form |
| Voucher list with filters | ⚠️ | |
| Voucher types: صرف (out) / استلام (in) / تحويل (transfer) | ⚠️ | Types exist in model, missing dedicated forms |

### Stocktaking / Inventory Count (ورقة الجرد)
| Feature | Status | Notes |
|---|---|---|
| Stocktaking list | ❌ | No model |
| Create stocktaking sheet | ❌ | Fields: warehouse, date, products, expected qty, actual qty, variance |
| Post stocktaking (apply adjustments) | ❌ | |

### Inventory Reports
| Feature | Status | Notes |
|---|---|---|
| Stock summary (ملخص عمليات المخزون) | ❌ | No report view |
| Estimated stock value (قيمة المخزون التقديرية) | ❌ | No report view |

---

## 4. MANUFACTURING MODULE (التصنيع)

### Bill of Materials (قوائم مواد الإنتاج)
| Feature | Status | Notes |
|---|---|---|
| BOM list | ✅ | |
| Create/edit BOM | ✅ | |
| BOM detail view (components, cost estimate) | ⚠️ | Model exists, no detail view |
| BOM versioning | ❌ | |

### Production Plans (خطط الإنتاج)
| Feature | Status | Notes |
|---|---|---|
| Production plan list | ❌ | No model (only WorkOrder) |
| Create production plan | ❌ | Fields: name, product, qty, start/end date, BOM, status |
| Production plan statuses management | ❌ | |

### Manufacturing Orders (أوامر التصنيع)
| Feature | Status | Notes |
|---|---|---|
| MO list | ✅ | WorkOrder |
| Create MO | ✅ | |
| MO detail (materials consumed, workstations) | ⚠️ | |
| Link MO to production plan | ❌ | |
| MO status management (حالات طلبات التصنيع) | ⚠️ | Basic statuses, no custom status management |

### Workstations (محطات العمل)
| Feature | Status | Notes |
|---|---|---|
| Workstation list | ❌ | No model |
| Add/edit workstation | ❌ | Fields: name, department, capacity, cost/hour |
| Assign workstation to MO | ❌ | |

### Indirect Costs (التكاليف غير المباشرة)
| Feature | Status | Notes |
|---|---|---|
| Indirect cost list | ❌ | No model |
| Add indirect cost | ❌ | Fields: name, amount, MO reference, account |

### Production Routes (مسارات الإنتاج)
| Feature | Status | Notes |
|---|---|---|
| Route list | ❌ | No model |
| Create route with steps | ❌ | |

### Manufacturing Settings
| Feature | Status | Notes |
|---|---|---|
| Default accounts for manufacturing | ❌ | |
| MO status customization | ❌ | |

---

## 5. CLIENTS MODULE (العملاء)

### Clients (العملاء)
| Feature | Status | Notes |
|---|---|---|
| Client list | ⚠️ | Basic in core? No dedicated client model found |
| Add/edit client | ⚠️ | |
| Missing fields | ❌ | credit limit, opening balance, price list, discount, payment terms, account code, branch, tags |
| Import clients (CSV) | ❌ | |
| Client detail page (invoices, payments, contacts, activity) | ❌ | |

### Client Contacts (قائمة الاتصال)
| Feature | Status | Notes |
|---|---|---|
| Contact list per client | ❌ | No ClientContact model |
| Add/edit contact | ❌ | Fields: name, job title, email, phone, primary flag |

### Appointments (المواعيد)
| Feature | Status | Notes |
|---|---|---|
| Appointment calendar view | ❌ | No model |
| Book appointment | ❌ | Fields: client, employee, date/time, duration, type, notes, status |
| Appointment statuses | ❌ | |
| Client appointment portal | ❌ | |

### CRM (إدارة علاقات العملاء)
| Feature | Status | Notes |
|---|---|---|
| CRM pipeline / follow-ups | ❌ | No model |
| Follow-up statuses | ❌ | |
| Lead management | ❌ | |

### Client Settings
| Feature | Status | Notes |
|---|---|---|
| Default payment terms for clients | ❌ | |
| Client numbering | ❌ | |

---

## 6. FINANCE MODULE (المالية)

### Expenses (المصروفات)
| Feature | Status | Notes |
|---|---|---|
| Expense list | ❌ | No model |
| Add expense | ❌ | Fields: date, category, amount, account, payment method, reference, notes, attachment |
| Expense categories (تصنيفات المصروفات) | ❌ | |
| Import expenses (CSV) | ❌ | |

### Payment Vouchers / Cash Receipts (سندات القبض)
| Feature | Status | Notes |
|---|---|---|
| Receipt voucher list | ❌ | No model |
| Add receipt voucher | ❌ | Fields: date, client/supplier, amount, account, type (قبض/صرف), reference |
| Receipt categories (تصنيفات السند قبضات) | ❌ | |
| Voucher settings (إعدادات سندات الصرف والقبض) | ❌ | |
| Voucher reports | ❌ | |

### Treasuries & Bank Accounts (خزائن وحسابات بنكية)
| Feature | Status | Notes |
|---|---|---|
| Treasury list | ❌ | No model |
| Add treasury (cash box) | ❌ | Fields: name, currency, opening balance, account |
| Add bank account | ❌ | Fields: bank name, account number, IBAN, currency, opening balance |
| Treasury view (transactions, balance) | ❌ | |

### Employee Custodies (عُهَد الموظفين)
| Feature | Status | Notes |
|---|---|---|
| Custody list | ❌ | No model |
| Add custody | ❌ | Fields: employee, amount, date, purpose, status (outstanding/settled) |

### Finance Settings (إعدادات المالية)
| Feature | Status | Notes |
|---|---|---|
| Default accounts for expenses/receipts | ❌ | |
| Reconciliation types (أنواع التسوية) | ❌ | |

---

## 7. ACCOUNTING MODULE (الحسابات العامة)

### Journal Entries (القيود اليومية)
| Feature | Status | Notes |
|---|---|---|
| Journal list | ✅ | |
| Add journal entry | ✅ | |
| Journal status (Draft/Posted/Void) | ✅ | |
| Missing | ⚠️ | No cost center selection on lines |

### Chart of Accounts (دليل الحسابات)
| Feature | Status | Notes |
|---|---|---|
| Account tree list | ✅ | Account + AccountGroup |
| Add/edit account | ✅ | |
| Missing fields | ⚠️ | No opening balance entry, no account type icons |

### Cost Centers (مراكز التكلفة)
| Feature | Status | Notes |
|---|---|---|
| Cost center list | ❌ | No model |
| Add cost center | ❌ | Fields: name, code, parent, is_active |

### Assets (الأصول)
| Feature | Status | Notes |
|---|---|---|
| Asset list | ❌ | No model |
| Add asset | ❌ | Fields: name, category, purchase date, cost, depreciation method, useful life, account |
| Depreciation schedule | ❌ | |
| Accounting assets (Accounting Assets page) | ❌ | |

### Accounting Settings
| Feature | Status | Notes |
|---|---|---|
| Default accounts config (AR, AP, cash, etc.) | ❌ | No settings model |
| Fiscal year management | ✅ | FiscalYear model |

---

## 8. HR MODULE (الموارد البشرية)

### Employees (الموظفين)
| Feature | Status | Notes |
|---|---|---|
| Employee list | ✅ | |
| Add/edit employee | ✅ | |
| Missing fields | ⚠️ | Missing: nationality, national ID, marital status, address, emergency contact, documents, photo |
| Employee asset custody | ❌ | No EmployeeAsset model |
| Employee roles management | ⚠️ | Role exists in core, no HR-specific role UI |

### Org Structure (الهيكل التنظيمي)
| Feature | Status | Notes |
|---|---|---|
| Departments | ✅ | Department model |
| Job titles (المسميات الوظيفية) | ❌ | No Designation model (only job_title text field) |
| Employment levels (مستويات وظيفية) | ❌ | No model |
| Employment types (أنواع الوظائف) | ❌ | No model (full-time/part-time/contract etc.) |

### Attendance (الحضور)
| Feature | Status | Notes |
|---|---|---|
| Attendance records | ✅ | Attendance model |
| Attendance days | ⚠️ | Basic date-based, missing: work hours policy |
| Attendance sheets / summary | ❌ | No AttendanceSheet aggregation model |
| Leave permissions (أذونات إجازة) | ❌ | No short-leave/permission model |
| Leave requests | ✅ | LeaveRequest |
| Shifts management (الورديات) | ❌ | No Shift model |
| Shift schedule | ❌ | |
| Attendance sessions log | ❌ | |
| Attendance settings | ❌ | |

### Payroll (المرتبات)
| Feature | Status | Notes |
|---|---|---|
| Payslips | ✅ | Basic Payslip model |
| Payrun (مسير الرواتب) | ❌ | No Payrun model (batch payslip generation) |
| Salary components (بنود الراتب: allowances, deductions) | ❌ | No SalaryComponent model |
| Salary structures / templates | ❌ | No SalaryStructure model |
| Loans / advances (السلف) | ❌ | No Loan model |
| Contracts (العقود) | ❌ | No Contract model |
| Payroll settings | ❌ | |

---

## 9. REPORTS MODULE (التقارير)

| Report | Status |
|---|---|
| Sales reports (invoices, payments, by client, by product) | ❌ |
| Purchase reports | ❌ |
| Accounting reports (P&L, balance sheet, trial balance) | ❌ |
| Manufacturing reports | ❌ |
| HR / employee reports | ❌ |
| Client reports | ❌ |
| Inventory reports | ❌ |
| Monthly payments report | ❌ |
| P&L report (cash basis) | ❌ |
| Monthly invoice summary | ❌ |
| Activity log | ⚠️ | AuditLog model exists, no report view |

---

## 10. SETTINGS & SYSTEM

| Feature | Status | Notes |
|---|---|---|
| General settings (company info, logo, colors) | ⚠️ | Company model, no logo/color fields |
| Branches (الفروع) | ❌ | No Branch model |
| SMTP settings | ❌ | No email config model |
| Payment gateways (طرق الدفع) | ❌ | No PaymentGateway model |
| Sequential numbering settings UI | ⚠️ | NumberSequence model, no UI |
| Tax settings UI | ⚠️ | TaxRate model, no settings UI |
| Printable templates | ❌ | No template management UI |
| Invoice template designs | ❌ | |
| Email templates | ❌ | No EmailTemplate model |
| Terms & conditions library | ❌ | No Terms model |
| Auto reminder rules | ❌ | No AutoReminder model |
| Documents / file manager | ❌ | No Document model |
| API key management | ❌ | |
| Activity log UI | ⚠️ | Model exists, no UI |
| System updates page | ❌ | |

---

## PRIORITY IMPLEMENTATION ORDER

Based on business impact, here's a suggested order:

### Phase 1 — Core selling & buying (highest impact)
1. **Client model** (missing entirely) + client list/add/edit pages
2. **Sales quote** model + pages
3. **Credit notes** + sales returns
4. **Expense** model + pages + categories
5. **Receipt/payment vouchers** (سندات القبض والصرف)
6. **Purchase request** + purchase quotation models

### Phase 2 — Inventory completion
7. **Stocktaking** model + pages
8. **Price lists**
9. **Product brands**
10. **Stock voucher forms** (IN/OUT forms)

### Phase 3 — HR completion
11. **Shifts** model + schedule
12. **Salary components** + salary structures
13. **Payrun** (batch payslips)
14. **Loans/advances**
15. **Contracts**
16. **Job titles / employment levels / types** (org structure)

### Phase 4 — Finance & Accounting
17. **Treasuries & bank accounts**
18. **Cost centers**
19. **Assets** + depreciation
20. **Employee custodies**

### Phase 5 — Manufacturing completion
21. **Production plans**
22. **Workstations**
23. **Indirect costs**
24. **Production routes**

### Phase 6 — Reports & Settings
25. **All reports** (sales, purchase, accounting, inventory, HR)
26. **Branches**
27. **Email templates + SMTP**
28. **Printable templates**
29. **Auto reminder rules**
30. **API keys**
