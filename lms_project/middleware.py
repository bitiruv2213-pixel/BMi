from __future__ import annotations

from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import get_language

from .translation_catalog import RUSSIAN_UI_TRANSLATIONS


class RuntimeTranslationMiddleware(MiddlewareMixin):
    """Apply a lightweight runtime UI translation layer for Russian."""

    content_types = ('text/html', 'application/json')

    def process_response(self, request, response):
        language = (get_language() or '').split('-', 1)[0]
        if language != 'ru':
            return response

        content_type = response.headers.get('Content-Type', '')
        if not any(kind in content_type for kind in self.content_types):
            return response

        if getattr(response, 'streaming', False):
            return response

        try:
            rendered = response.content.decode(response.charset or 'utf-8')
        except (AttributeError, UnicodeDecodeError):
            return response

        translated = rendered
        for source, target in sorted(RUSSIAN_UI_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
            translated = translated.replace(source, target)

        if translated != rendered:
            response.content = translated.encode(response.charset or 'utf-8')
            if 'Content-Length' in response.headers:
                response.headers['Content-Length'] = str(len(response.content))

        return response
