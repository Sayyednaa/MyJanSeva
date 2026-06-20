"""My Jan Seva — Settings Package"""
from decouple import config

# Dynamically load the correct environment settings package
DEBUG = config('DEBUG', default=True, cast=bool)

if DEBUG:
    from .dev import *
else:
    from .production import *
