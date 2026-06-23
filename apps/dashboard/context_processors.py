"""Dashboard context processors"""
from .models import PrintSettings

def print_settings(request):
    if request.user.is_authenticated:
        settings_obj, created = PrintSettings.objects.get_or_create(user=request.user)
        # 528px is 5.5in, 334px is 334/96 = 3.4791666666666665in
        scale_x = settings_obj.ration_card_width / 5.5
        scale_y = settings_obj.ration_card_height / (334.0 / 96.0)
        return {
            'print_settings': settings_obj,
            'ration_scale_x': round(scale_x, 4),
            'ration_scale_y': round(scale_y, 4),
        }
    return {
        'print_settings': {
            'farmer_id_width': 3.22,
            'farmer_id_height': 2.15,
            'ration_card_width': 3.71,
            'ration_card_height': 2.34,
        },
        'ration_scale_x': round(3.71 / 5.5, 4),
        'ration_scale_y': round(2.34 / (334.0 / 96.0), 4),
    }
