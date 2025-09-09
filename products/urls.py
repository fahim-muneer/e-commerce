from django.urls import path
from .views import ProductView,ProductAdding,ProductUpdate,ProductDelete,ProductDetail


urlpatterns = [
    path('product_list/',ProductView.as_view(),name="product_list"),
    path('product_add/',ProductAdding.as_view(),name="product_add"),
    path('<pk>/product_update/',ProductUpdate.as_view(),name="proiduct_update"),
    path('<pk>/product_delete/',ProductDelete.as_view(),name="proiduct_delete"),
    path('<pk>/product_details/',ProductDetail.as_view(),name="proiduct_details"),

]
