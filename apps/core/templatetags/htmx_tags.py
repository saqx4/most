from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def hx_delete(url, confirm_msg, swap="none"):
    """Render a form wrapper for HTMX DELETE/POST actions.

    Usage: {% hx_delete 'inventory:product_delete' p.pk 'Delete this?' %}
    Outputs opening <form> tag with hx-post + hx-confirm.
    """
    return format_html(
        '<form method="post" action="{}" class="inline" '
        'hx-post="{}" '
        "hx-headers='{{&quot;X-CSRFToken&quot;: &quot;{{ csrf_token }}&quot;}}' "
        'hx-confirm="{}" '
        'hx-swap="{}">',
        url, url, confirm_msg, swap,
    )


@register.simple_tag
def hx_post(url, confirm_msg="", swap="none"):
    """Render a form wrapper for HTMX POST actions.

    Usage: {% hx_post 'accounting:journal_post' p.pk 'Post this entry?' %}
    Outputs opening <form> tag with hx-post.
    """
    attrs = (
        '<form method="post" action="{}" class="inline" '
        'hx-post="{}" '
        "hx-headers='{{&quot;X-CSRFToken&quot;: &quot;{{ csrf_token }}&quot;}}' "
        'hx-swap="{}"'
    ).format(url, url, swap)
    if confirm_msg:
        attrs += ' hx-confirm="{}"'.format(confirm_msg)
    attrs += ">"
    return format_html(attrs)


@register.simple_tag
def htmx_indicator():
    """Return the standard HTMX indicator CSS."""
    return format_html(
        '<style>'
        ".htmx-indicator {{ opacity: 0; }}"
        ".htmx-request .htmx-indicator {{ opacity: 1; }}"
        ".htmx-request.htmx-indicator {{ opacity: 1; }}"
        "</style>"
    )
