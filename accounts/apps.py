from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        from django.conf import settings

        # Ensure Site object exists for allauth
        from django.db import connection
        try:
            table_names = connection.introspection.table_names()
            if 'django_site' not in table_names:
                return

            from django.contrib.sites.models import Site

            Site.objects.get_or_create(id=settings.SITE_ID, defaults={
                'domain': 'lmsuzplatform.uz',
                'name': 'LMS Platform',
            })
        except Exception:
            pass
