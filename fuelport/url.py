from .views import loginView,registerView,adminPriceManagementView,adminStationView,adminAddStation,litreLotView,dashBoardView,purchaseSuccessView,buyLitreView, proceedToPaystack,fromPayStackRedirectView,purchaseCreateView
from django.urls import path

urlpatterns = [
    # path('',aboutView, name='fuelport-about'),
    path("",dashBoardView,name='user-dashboard'),
    path("buylitre/",buyLitreView,name='buy-litre'),
    path("purchaselitre/<int:pid>/",purchaseSuccessView,name='purchase-litre'),
    path("dashboard/",dashBoardView,name='dashboard'),
    path("litrelot/",litreLotView,name='litre-lot'),
    path("login/",loginView,name='user-login'),
    path("register/",registerView,name='user-register'),
    path("staff/price-management/",adminPriceManagementView,name='admin-price-management'),
    path("staff/station/",adminStationView,name='admin-station-management'),
    path("staff/addStation/",adminAddStation, name='admin-add-newstation'),
    path("paystack-success-redirect/",fromPayStackRedirectView, name='paystack-redirect'),
    path("initialize-payment/", proceedToPaystack, name = "payment-initialize"),
    path('purchase/create/', purchaseCreateView, name="purchase-create"),
]
