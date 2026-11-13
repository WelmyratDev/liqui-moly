from django.contrib.sitemaps import Sitemap
from .models import Product, Category


class ProductSitemap(Sitemap):

    changefreq = "weekly"

    priority = 0.8


    def items(self):
        return Product.objects.all()


    def location(self, obj):
        return obj.get_absolute_url()



class CategorySitemap(Sitemap):

    changefreq = "weekly"

    priority = 0.8


    def items(self):
        return Category.objects.all()


    def location(self, obj):
        return obj.get_absolute_url()