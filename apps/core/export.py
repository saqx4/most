import csv

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


def export_to_csv(queryset, fields, filename='export.csv'):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    headers = [f.replace('_', ' ').title() for f in fields]
    writer.writerow(headers)
    for obj in queryset:
        row = []
        for f in fields:
            value = obj
            for attr in f.split('__'):
                if value is None:
                    break
                value = getattr(value, attr, None)
            if hasattr(value, 'strftime'):
                value = value.strftime('%Y-%m-%d')
            elif hasattr(value, 'pk'):
                value = str(value)
            elif value is None:
                value = ''
            row.append(value)
        writer.writerow(row)
    return response


def export_to_excel(queryset, fields, filename='export.xlsx'):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Export'

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='4F46E5', end_color='4F46E5', fill_type='solid')

    headers = [f.replace('_', ' ').title() for f in fields]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill

    for row_idx, obj in enumerate(queryset, 2):
        for col_idx, f in enumerate(fields, 1):
            value = obj
            for attr in f.split('__'):
                if value is None:
                    break
                value = getattr(value, attr, None)
            if hasattr(value, 'strftime'):
                value = value.strftime('%Y-%m-%d')
            elif hasattr(value, 'pk'):
                value = str(value)
            elif value is None:
                value = ''
            ws.cell(row=row_idx, column=col_idx, value=value)

    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = min(max_length + 2, 40)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response
