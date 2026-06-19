"""Management command to seed default services and ID card templates"""
from django.core.management.base import BaseCommand
from apps.pricing.models import Service, ServiceCategory
from apps.id_cards.models import IDCardTemplate


class Command(BaseCommand):
    help = 'Seed default services and ID card templates'

    def handle(self, *args, **options):
        # Service Categories
        cats = {}
        for name, slug, icon in [
            ('Photo Services', 'photo', 'bi-camera'),
            ('ID Cards', 'id-cards', 'bi-card-heading'),
            ('PDF Tools', 'pdf', 'bi-file-pdf'),
        ]:
            cat, _ = ServiceCategory.objects.get_or_create(slug=slug, defaults={'name': name, 'icon': icon})
            cats[slug] = cat

        # Services
        services = [
            ('Passport Photo', 'passport-photo', 3, 'photo'),
            ('Photo Sheet', 'photo-sheet', 3, 'photo'),
            ('Signature Resize', 'signature-resize', 2, 'photo'),
            ('Aadhaar PVC', 'aadhaar-pvc', 5, 'id-cards'),
            ('PAN PVC', 'pan-pvc', 5, 'id-cards'),
            ('Voter PVC', 'voter-pvc', 5, 'id-cards'),
            ('ID Card', 'id-card', 5, 'id-cards'),
            ('PDF Merge', 'pdf-merge', 2, 'pdf'),
            ('PDF Split', 'pdf-split', 2, 'pdf'),
            ('PDF Compress', 'pdf-compress', 2, 'pdf'),
            ('PDF Rotate', 'pdf-rotate', 1, 'pdf'),
            ('Image to PDF', 'img-to-pdf', 2, 'pdf'),
            ('PDF Password', 'pdf-password', 2, 'pdf'),
        ]
        for name, slug, price, cat_slug in services:
            Service.objects.get_or_create(slug=slug, defaults={
                'name': name, 'price': price, 'category': cats[cat_slug],
            })

        # ID Card Templates
        id_templates = [
            ('Aadhaar PVC Card', 'aadhaar_pvc', '#1a237e', '#ffca28'),
            ('PAN PVC Card', 'pan_pvc', '#0d47a1', '#ffffff'),
            ('Voter ID PVC', 'voter_pvc', '#1b5e20', '#ffeb3b'),
            ('School ID Card', 'school_id', '#4a148c', '#e1bee7'),
            ('Employee ID Card', 'employee_id', '#263238', '#80deea'),
        ]
        for name, ctype, bg, accent in id_templates:
            IDCardTemplate.objects.get_or_create(card_type=ctype, defaults={
                'name': name, 'front_bg_color': bg, 'accent_color': accent,
            })

        self.stdout.write(self.style.SUCCESS(
            f'Seeded: {len(services)} services, {len(id_templates)} ID templates'
        ))
