import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_invoice_email(invoice):
    company = invoice.company
    subject = f'Invoice {invoice.number} from {company.name}'
    html_message = render_to_string('emails/invoice.html', {
        'invoice': invoice,
        'company': company,
    })
    plain_message = f'Please find attached invoice {invoice.number}.'

    msg = EmailMessage(
        subject=subject,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invoice.customer.email] if invoice.customer.email else [],
    )
    msg.content_subtype = 'html'
    msg.body = html_message

    try:
        from apps.core.pdf import render_to_pdf
        pdf_response = render_to_pdf('pdf/invoice.html', {
            'invoice': invoice,
            'company': company,
        }, filename=f'{invoice.number}.pdf')
        msg.attach(f'{invoice.number}.pdf', pdf_response.content, 'application/pdf')
    except Exception as e:
        logger.warning(f'Could not attach PDF: {e}')

    msg.send(fail_silently=True)
    return True


def send_payment_reminder(customer, invoices):
    company = invoices[0].company if invoices else None
    if not company:
        return False

    subject = f'Payment Reminder - Outstanding Invoices'
    html_message = render_to_string('emails/payment_reminder.html', {
        'customer': customer,
        'invoices': invoices,
        'company': company,
        'total_due': sum(inv.amount_due for inv in invoices),
    })

    msg = EmailMessage(
        subject=subject,
        body=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[customer.email] if customer.email else [],
    )
    msg.content_subtype = 'html'
    msg.send(fail_silently=True)
    return True


def send_payslip_email(payslip):
    employee = payslip.employee
    company = payslip.company
    subject = f'Payslip for {payslip.period}'
    html_message = render_to_string('emails/payslip.html', {
        'payslip': payslip,
        'employee': employee,
        'company': company,
    })

    recipient = employee.email
    if not recipient:
        return False

    msg = EmailMessage(
        subject=subject,
        body=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    msg.content_subtype = 'html'

    try:
        from apps.core.pdf import render_to_pdf
        pdf_response = render_to_pdf('pdf/payslip.html', {
            'payslip': payslip,
            'company': company,
        }, filename=f'payslip-{employee.employee_code}-{payslip.period}.pdf')
        msg.attach(f'payslip-{employee.employee_code}-{payslip.period}.pdf', pdf_response.content, 'application/pdf')
    except Exception as e:
        logger.warning(f'Could not attach payslip PDF: {e}')

    msg.send(fail_silently=True)
    return True
