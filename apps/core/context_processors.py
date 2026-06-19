"""Core context processor — site-wide settings"""


def site_settings(request):
    return {
        'SITE_NAME': 'Jan Seva Workspace',
        'SITE_TAGLINE': 'Complete Document & ID Services Platform',
    }
