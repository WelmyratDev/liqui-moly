from django.core.management.base import BaseCommand

from cart.images import thumbnail_url
from cart.models import Banner, Category, Product

PRODUCT_WIDTHS = (240, 480, 800)
CATEGORY_WIDTHS = (160,)
BANNER_WIDTHS = (800, 1200, 1920)


class Command(BaseCommand):
    help = "Pre-generate WebP thumbnails for products, categories and banners (run after deploy)."

    def handle(self, *args, **options):
        done = 0
        for product in Product.objects.exclude(image="").exclude(image__isnull=True).iterator():
            for w in PRODUCT_WIDTHS:
                thumbnail_url(product.image, w)
            done += 1
        for category in Category.objects.exclude(image="").exclude(image__isnull=True):
            for w in CATEGORY_WIDTHS:
                thumbnail_url(category.image, w)
            done += 1
        for banner in Banner.objects.all():
            for field in (banner.image, banner.image_sm):
                if field:
                    for w in BANNER_WIDTHS:
                        thumbnail_url(field, w)
            done += 1
        self.stdout.write(self.style.SUCCESS(f"Thumbnails ready for {done} objects."))
