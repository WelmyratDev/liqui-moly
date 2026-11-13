from import_export import resources
from .models import Product, Category


class ProductResource(resources.ModelResource):

    class Meta:
        model = Product
        exclude = (
            "created_at",
            "updated_at",
        )


class CategoryResource(resources.ModelResource):

    class Meta:
        model = Category