"""Core context processor — site-wide settings"""


def site_settings(request):
    return {
        'SITE_NAME': 'My Jan Seva',
        'SITE_TAGLINE': 'Complete Document & ID Services Platform',
    }
