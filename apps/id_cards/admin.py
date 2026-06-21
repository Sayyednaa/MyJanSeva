"""ID Cards admin"""
from django.contrib import admin
from .models import IDCardTemplate, IDCardGeneration, FarmerIDCard

@admin.register(IDCardTemplate)
class IDCardTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'card_type', 'is_active', 'created_at')
    list_filter = ('card_type', 'is_active')

@admin.register(IDCardGeneration)
class IDCardGenerationAdmin(admin.ModelAdmin):
    list_display = ('custom_name', 'user', 'template', 'created_at')

@admin.register(FarmerIDCard)
class FarmerIDCardAdmin(admin.ModelAdmin):
    list_display = ('farmer_id', 'name_en', 'user', 'mobile', 'print_count', 'created_at')
    list_filter = ('user', 'gender', 'created_at')
    search_fields = ('farmer_id', 'name_en', 'name_hi', 'mobile', 'aadhaar', 'user__username', 'user__email')
    ordering = ('-created_at',)
    
    def image_tag(self, obj):
        from django.utils.safestring import mark_safe
        if obj.photo:
            return mark_safe(f'<img src="{obj.photo}" width="100" style="border-radius: 8px; border: 1px solid #ccc;" />')
        return "No Photo"
    image_tag.short_description = 'Farmer Photo Preview'
    
    readonly_fields = ('created_at', 'updated_at', 'image_tag')
    
    fieldsets = (
        ('Operator Info', {
            'fields': ('user', 'print_count')
        }),
        ('Farmer Details', {
            'fields': ('farmer_id', 'name_en', 'name_hi', 'dob', 'gender', 'mobile', 'aadhaar', 'address')
        }),
        ('Photo & Land Details', {
            'fields': ('image_tag', 'photo', 'land_details')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

