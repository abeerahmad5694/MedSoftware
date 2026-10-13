from django.contrib import admin
from .models import BarcodConfig , Features
# Register your models here.


# @admin.register(BarcodConfig)
# class barcode_config_admin(admin.ModelAdmin):
#     list_display = ('user',"price_base",'total_bc_digits','left_delete','right_delete','item_bc','kg','grm')


# @admin.register(Features)
# class FeaturesAdmin(admin.ModelAdmin):
#     list_display= ('user',"pos_discount_per_item","pos_load_prv_bill",'pos_disc_flat_limit')
#     list_editable = ("pos_discount_per_item","pos_load_prv_bill",'pos_disc_flat_limit')