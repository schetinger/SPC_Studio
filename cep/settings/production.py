"""
Production settings — Neon PostgreSQL + Upstash Redis + WhiteNoise.

Used on Render via: DJANGO_SETTINGS_MODULE=cep.settings.production
Requires env vars: SECRET_KEY, DATABASE_URL, REDIS_URL
"""

import os
import dj_database_url
from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = [
    '.onrender.com',
]

# --- Banco de dados (Neon PostgreSQL) ---
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True,
    )
}

# --- Cache (Upstash Redis) ---
REDIS_URL = os.environ.get('REDIS_URL', '')
if REDIS_URL.startswith('redis://'):
    REDIS_URL = REDIS_URL.replace('redis://', 'rediss://', 1)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

# --- Arquivos estáticos (WhiteNoise) ---
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# WhiteNoise middleware (inserido logo após SecurityMiddleware)
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
