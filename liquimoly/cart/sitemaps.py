from django.contrib.sitemaps import Sitemap

from .models import Category, Product


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    i18n = False

    def items(self):
        # The same product exists once per region with the same slug:
        # list every URL only once.
        seen = set()
        unique = []
        for product in Product.objects.exclude(slug__isnull=True).exclude(slug="").order_by("slug", "id").only(
            "id", "slug", "updated_at"
        ):
            if product.slug not in seen:
                seen.add(product.slug)
                unique.append(product)
        return unique

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Category.objects.exclude(slug__isnull=True).exclude(slug="").order_by("sort_order", "id")

    def location(self, obj):
        return obj.get_absolute_url()
