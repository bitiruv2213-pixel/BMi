import os
from pathlib import Path
import sys

try:
    import dj_database_url
    DJ_DATABASE_URL_AVAILABLE = True
except ImportError:
    DJ_DATABASE_URL_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ('true', '1', 'yes', 'on')


def _env_list(name, default=None):
    value = os.environ.get(name, '')
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]


def _load_dotenv(path):
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
    except Exception:
        pass


_load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me')

IS_PRODUCTION_HINT = bool(
    os.environ.get('RAILWAY_ENVIRONMENT')
    or os.environ.get('RAILWAY_PROJECT_ID')
    or os.environ.get('DATABASE_URL')
)
IS_TESTING = 'test' in sys.argv

DEBUG = _env_bool('DEBUG', default=not IS_PRODUCTION_HINT)

ALLOWED_HOSTS = _env_list('ALLOWED_HOSTS', default=[
    '.railway.app',
    '.up.railway.app',
    'localhost',
    '127.0.0.1',
    'www.lmsuzplatform.uz',
    'lmsuzplatform.uz',
])

CSRF_TRUSTED_ORIGINS = _env_list('CSRF_TRUSTED_ORIGINS', default=[
    'https://*.railway.app',
    'https://*.up.railway.app',
    'https://www.lmsuzplatform.uz',
    'https://lmsuzplatform.uz',
])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'accounts',
    'courses',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'lms_project.middleware.RuntimeTranslationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lms_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'lms_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_PRIVATE_URL') or os.environ.get('DATABASE_PUBLIC_URL')
if DATABASE_URL and DJ_DATABASE_URL_AVAILABLE:
    DATABASES['default'] = dj_database_url.parse(DATABASE_URL, conn_max_age=600)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz'
LANGUAGES = [
    ('uz', "O'zbekcha"),
    ('ru', 'Русский'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG or IS_TESTING
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_SERVE_DJANGO = _env_bool('MEDIA_SERVE_DJANGO', default=DEBUG)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==================== AUTHENTICATION SETTINGS ====================
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS['google']['APP'] = {
        'client_id': GOOGLE_CLIENT_ID,
        'secret': GOOGLE_CLIENT_SECRET,
    }

# ==================== EMAIL CONFIGURATION ====================
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = _env_bool('EMAIL_USE_TLS', default=True)
EMAIL_USE_SSL = _env_bool('EMAIL_USE_SSL', default=False)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '').strip()
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '').strip()
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'LMS Platform <noreply@lms.uz>')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', DEFAULT_FROM_EMAIL)

# Agar SMTP credential berilgan bo'lsa, Gmail orqali haqiqiy email yuboriladi.
# Aks holda lokal development uchun email console'da ko'rinadi.
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Password Reset Timeout (24 hours)
PASSWORD_RESET_TIMEOUT = 86400

# ==================== AI API ====================
AI_API_KEY = (
    os.environ.get('AI_API_KEY')
    or os.environ.get('MOONSHOT_API_KEY')
    or os.environ.get('GEMINI_API_KEY')
    or os.environ.get('GOOGLE_API_KEY')
    or os.environ.get('GOOGLE_GENERATIVE_AI_API_KEY')
    or ''
)
AI_API_BASE_URL = (
    os.environ.get('AI_API_BASE_URL')
    or os.environ.get('MOONSHOT_BASE_URL')
    or 'https://api.moonshot.ai/v1'
).rstrip('/')
AI_MODEL = (
    os.environ.get('AI_MODEL')
    or os.environ.get('MOONSHOT_MODEL')
    or 'kimi-k2.5'
)

# Public base URL (emails/certificates)
SITE_URL = os.environ.get('SITE_URL', 'http://127.0.0.1:8000')

# Optional certificate branding assets (PNG/JPG absolute paths)
CERTIFICATE_LOGO_PATH = os.environ.get('CERTIFICATE_LOGO_PATH')
CERTIFICATE_SIGNATURE_LEFT_PATH = os.environ.get('CERTIFICATE_SIGNATURE_LEFT_PATH')
CERTIFICATE_SIGNATURE_RIGHT_PATH = os.environ.get('CERTIFICATE_SIGNATURE_RIGHT_PATH')

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
