from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Station
from .models import FuelPrice
from .models import LitrePurchase
from .models import LitreWallet
from .models import LitreLot
from .models import FuelRedemption
from .models import initializePaymentMethod

# Register your models here.
admin.site.register(initializePaymentMethod)
admin.site.register(Station)
admin.site.register(FuelPrice)
class FuelPriceAdmin(admin.ModelAdmin):
    list_display = ('price_per_litre', 'effective_from', 'set_by')
admin.site.register(LitrePurchase)
admin.site.register(LitreWallet)
admin.site.register(LitreLot)
admin.site.register(FuelRedemption)