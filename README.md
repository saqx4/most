# ERP System

A full-featured, modular ERP system built with Django 6.1 for small and medium businesses.

## Modules

| Module | What it does |
|---|---|
| **Accounting & Finance** | Chart of accounts, journal entries, fiscal years, trial balance, income statement, balance sheet |
| **Inventory** | Products, stock levels, stock adjustments, low-stock alerts |
| **Sales & CRM** | Customers, sales orders, sales invoices, quotes |
| **Purchasing** | Suppliers, purchase orders, goods receiving |
| **Manufacturing** | Bills of materials, work orders, production |
| **HR & Payroll** | Employees, departments, contracts, payslips |
| **Reports & Dashboard** | KPI dashboard, revenue trends, AR aging, inventory valuation |

## Tech Stack

- **Backend**: Django 6.1, Python 3.13
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Frontend**: Tailwind CSS, HTMX, Chart.js
- **PDF Generation**: xhtml2pdf
- **Export**: CSV, Excel (.xlsx) via openpyxl
- **i18n**: English + Arabic (RTL)
- **Deployment**: Docker, Gunicorn, Nginx

## Getting Started

### Prerequisites

- Python 3.13+
- pip
- Git (optional)

### Local Setup

```bash
# Clone or copy the project
cd C:\erp  # or your chosen directory

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set up environment
copy .env.example .env  # or edit .env directly

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start development server
python manage.py runserver 8030
```

Open **http://127.0.0.1:8030** and log in.

### Docker Setup

```bash
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Open **http://localhost:8000**.

## Default Users

| Username | Password | Role |
|---|---|---|
| `admin` | `admin12345` | Administrator |
| `ops` | `demo1234` | Operator |

## Configuration (.env)

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=                    # blank = SQLite, set for PostgreSQL
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
TIMEZONE=UTC
```

## How the Database Works

Your ERP uses **one database** (PostgreSQL in production). All users log into the **same system** and see the **same data**.

- **Single company** — no multi-tenant separation needed
- Every user sees all products, invoices, employees, etc.
- **Roles** control what each user can **do** (view-only vs. edit vs. admin)

### Roles

| Role | Can do |
|---|---|
| Administrator | Full access to everything |
| Manager | Full access (same as admin) |
| Accountant | Accounting + Reports |
| Sales | Customers, invoices, quotes |
| Purchasing | Suppliers, purchase orders |
| Warehouse | Stock management |
| Manufacturing | BOMs, work orders |
| HR | Employees, payslips |
| Viewer | Read-only access |

## Deployment

### Production Checklist

1. Set `DEBUG=False` in `.env`
2. Set a strong `SECRET_KEY`
3. Set `DATABASE_URL` to your PostgreSQL connection string
4. Set `ALLOWED_HOSTS` to your domain (e.g., `yourdomain.com`)
5. Enable SSL: `SECURE_SSL_REDIRECT=True`
6. Configure email (SMTP) for invoice/payslip sending
7. Collect static files: `python manage.py collectstatic`
8. Run with Gunicorn behind Nginx (see `gunicorn_config.py` and `nginx.conf`)

### Will My Manager See the Same Data?

**Yes.** When deployed to a server/domain:
- Everyone logs into the same URL
- All users see the **same data** — everything is shared
- What each user can **do** depends on their **role** (admin, sales, viewer, etc.)

## Project Structure

```
C:\erp\
├── erp/                 # Django project settings
├── apps/
│   ├── core/            # Users, Company, Roles, utilities
│   ├── accounting/      # Chart of accounts, journal entries
│   ├── inventory/       # Products, stock levels
│   ├── sales/           # Customers, invoices, orders, quotes
│   ├── purchasing/      # Suppliers, purchase orders
│   ├── manufacturing/   # BOMs, work orders
│   ├── hr/              # Employees, departments, payslips
│   └── reports/         # Dashboard, trial balance, statements
├── templates/           # HTML templates (Tailwind + HTMX)
├── locale/              # Arabic translations
├── static/              # CSS, JS, images
├── tests/               # 94 automated tests
├── Dockerfile           # Container build
├── docker-compose.yml   # Production stack
├── nginx.conf           # Reverse proxy config
├── gunicorn_config.py   # App server config
├── requirements.txt     # Python dependencies
└── .env                 # Environment configuration
```

## API / Programmatic Access

This ERP is a traditional server-rendered app (not a REST API). All interaction happens through web pages and forms.

## License

Internal use only.
