"""
URL configuration for shop project.
"""
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

handler404 = 'custom_admin.views.custom_404'
handler500 = 'custom_admin.views.custom_500'
handler403 = 'custom_admin.views.custom_403'
handler400 = 'custom_admin.views.custom_400'


urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('custom_admin/', include('custom_admin.urls')),
    path('category/', include('category.urls')),
    path('customer/', include('customer.urls')),
    path('', include('home.urls')),
    path('products/', include('products.urls')),
    path('user_panel/', include('user_panel.urls')),
    path('orders/', include('orders.urls')),
    path('wish-list/', include('wish_list.urls')),
    path('varients/', include('varients.urls')),
    path('offer/', include('offer.urls')),
    path('payment/', include('payment.urls')),
    path('wallet/', include('wallet.urls')),
    path('refferal/', include('refferal.urls')),
    path('coupon/', include('coupon.urls')),
    path('banner/',include('banner.urls'))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    print("DEBUG = True")
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    print("Debug = False")
    # Force Django to serve them even when DEBUG=False (for local testing only)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)