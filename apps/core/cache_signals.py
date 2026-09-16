from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save)
@receiver(post_delete)
def auto_invalidate_cache(sender, **kwargs):
    """Auto-invalidate ERP caches when any business model is saved or deleted."""
    if sender._meta.app_label in ('auth', 'contenttypes', 'sessions'):
        return
    business_apps = {'accounting', 'inventory', 'sales', 'purchasing', 'manufacturing', 'hr'}
    if sender._meta.app_label in business_apps:
        cache.clear()
