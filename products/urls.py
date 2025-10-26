from django.urls import path
from .views import ProductView,ProductAdding,ProductUpdate,ProductDelete,ProductDetail,AddProductVariant,upload_cropped_image
from.views import DeleteProductVariant,UpdateProductVariant
from django.contrib.admin.views.decorators import staff_member_required

urlpatterns = [
    path('product_list/',staff_member_required(ProductView.as_view(),login_url='index'),name="product_list"),
    path('product_add/',staff_member_required(ProductAdding.as_view(),login_url='index'),name="product_add"),
    path('<pk>/product_update/',staff_member_required(ProductUpdate.as_view(),login_url='index'),name="product_update"),
    path('<pk>/product_delete/',staff_member_required(ProductDelete.as_view(),login_url='index'),name="product_delete"),
    path('<pk>/product_details/',staff_member_required(ProductDetail.as_view(),login_url='index'),name="product_details"),
    path('<int:pid>/add_product-variant/',staff_member_required(AddProductVariant.as_view(),login_url='index'),name="add_product_variants"),
    path('upload-cropped-image/',staff_member_required(upload_cropped_image,login_url='index'), name='upload_cropped_image'),
    path('<int:pk>/delete-product-variant/',staff_member_required(DeleteProductVariant.as_view(),login_url='index'),name="delete_product_variant"),
    path('<int:pk>/update-product-variant/',staff_member_required(UpdateProductVariant.as_view(),login_url='index'),name="update_product_variant"),

]
