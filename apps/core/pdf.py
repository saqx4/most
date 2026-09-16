"""PDF rendering utilities using xhtml2pdf."""
from io import BytesIO

from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa


def render_to_pdf(template_name, context, filename='document.pdf'):
    """Render a Django template to PDF and return an HttpResponse."""
    html_string = render_to_string(template_name, context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_string.encode('utf-8')), result)
    if pdf.err:
        return HttpResponse('PDF generation error', status=500)
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
