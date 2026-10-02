from django.urls import path

from .views import product_list


urlpatterns = [
    # GET /products/
    # POST /products/
    path("", product_list, name="product-list"),

    # PUT /products/<id>/
    path(
        "<int:product_id>/",
        product_list,
        name="product-detail",
    ),
]