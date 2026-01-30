import os
from pathlib import Path
from datetime import timedelta

import dj_database_url
from decouple import config

# =========================
# BASE
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent

# =========================
# SECURITY
# =========================
SECRET_KEY = os.environ.get("SECRET_KEY", "unsafe-secret-key")

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = ["*", ".onrender.com"]

# =========================
# APPLICATIONS
# =========================
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',
]

LOCAL_APPS = [
    'authentication',
    'core',
    'transactions',
    'administration',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =========================
# MIDDLEWARE
# =========================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# =========================
# URLS / WSGI
# =========================
ROOT_URLCONF = 'Backend.urls'
WSGI_APPLICATION = 'Backend.wsgi.application'

# =========================
# TEMPLATES
# =========================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# =========================
# DATABASE
# =========================
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# =========================
# AUTH
# =========================
AUTH_USER_MODEL = 'authentication.Utilisateur'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =========================
# I18N
# =========================
LANGUAGE_CODE = 'fr'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_TZ = True

# =========================
# STATIC & MEDIA
# =========================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =========================
# DEFAULT PK
# =========================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =========================
# DJANGO REST FRAMEWORK
# =========================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}

# =========================
# JWT
# =========================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=100),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=200),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'TOKEN_OBTAIN_SERIALIZER': 'authentication.serializers.CustomTokenObtainPairSerializer',
}

# =========================
# CORS
# =========================
CORS_ALLOW_ALL_ORIGINS = True  # OK pour Render + API publique

# =========================
# PARAMÈTRES MUTUELLE
# =========================
MUTUELLE_DEFAULTS = {
    'INSCRIPTION_AMOUNT': config('DEFAULT_INSCRIPTION_AMOUNT', default=150000, cast=int),
    'SOLIDARITE_AMOUNT': config('DEFAULT_SOLIDARITE_AMOUNT', default=10000, cast=int),
    'INTEREST_RATE': config('DEFAULT_INTEREST_RATE', default=3.0, cast=float),
    'LOAN_MULTIPLIER': config('DEFAULT_LOAN_MULTIPLIER', default=5, cast=int),
    'EXERCISE_DURATION_MONTHS': config('DEFAULT_EXERCISE_DURATION_MONTHS', default=12, cast=int),
}

# =========================
# LOGGING
# =========================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
    