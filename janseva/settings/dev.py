"""Development settings"""
from .base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Don't use compressed storage in dev
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
