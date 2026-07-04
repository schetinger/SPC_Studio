"""
Development settings — SQLite + InMemoryChannelLayer.

Used locally via: DJANGO_SETTINGS_MODULE=cep.settings.development
"""

from .base import *  # noqa: F401,F403

DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-qzg#3f8o9w63_$@4&0zdkovq7)-1xax_3tiu2gf^!t&k^*n01j'

ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
