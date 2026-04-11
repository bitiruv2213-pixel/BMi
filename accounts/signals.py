from django.conf import settings


def ensure_default_site(sender, **kwargs):
    try:
        from django.contrib.sites.models import Site

        Site.objects.get_or_create(
            id=settings.SITE_ID,
            defaults={
                'domain': 'lmsuzplatform.uz',
                'name': 'LMS Platform',
            },
        )
    except Exception:
        return
