import shutil
import tempfile
from decimal import Decimal

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from cart.models import Banner, Brand, CartItem, Category, Order, OrderItem, Place, Product, Rating
from users.models import User

TEMP_MEDIA = tempfile.mkdtemp()


def png_bytes(size=(1200, 1200), color=(200, 30, 30, 255)):
    import io

    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, "PNG")
    return buf.getvalue()


@override_settings(
    MEDIA_ROOT=TEMP_MEDIA,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    SECURE_SSL_REDIRECT=False,
)
class ShopTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.ashgabat = Place.objects.create(title_tm="Ashgabat", title_ru="Ашхабад")
        self.mary = Place.objects.create(title_tm="Mary", title_ru="Мары")
        self.oils = Category.objects.create(title_tm="Motor ýaglary", title_ru="Моторные масла")
        self.params_cat = Category.objects.create(title_tm="Hyzmat", requires_parameters=True)
        self.product = Product.objects.create(
            place=self.ashgabat, category=self.oils, title_tm="Molygen 5W-40", price=Decimal("250.00"), is_top=True
        )
        self.product_mary = Product.objects.create(
            place=self.mary, category=self.oils, title_tm="Molygen 5W-40", price=Decimal("260.00")
        )
        self.client = Client()

    def visitor(self, place=None):
        client = Client()
        if place:
            client.cookies["place_id"] = str(place.pk)
        return client


class PageTests(ShopTestCase):
    def test_pages_render_with_and_without_region(self):
        urls = [
            reverse("cart:home"),
            reverse("cart:product-list"),
            reverse("cart:category-detail", args=[self.oils.slug]),
            reverse("cart:product_detail", args=[self.product.slug]),
            reverse("cart:search-item") + "?query=moly",
            reverse("cart:cart"),
            reverse("cart:reviews"),
            reverse("cart:about-company"),
        ]
        for client in (self.visitor(), self.visitor(self.ashgabat)):
            for url in urls:
                with self.subTest(url=url):
                    self.assertEqual(client.get(url).status_code, 200)

    def test_garbage_place_cookie_does_not_crash(self):
        for value in ("abc", "999", "1; DROP", ""):
            client = Client()
            client.cookies["place_id"] = value
            with self.subTest(value=value):
                self.assertEqual(client.get(reverse("cart:home")).status_code, 200)
                self.assertEqual(client.get(reverse("cart:search-item") + "?query=a").status_code, 200)

    def test_product_page_without_region_is_shown_not_redirected(self):
        response = self.visitor().get(reverse("cart:product_detail", args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Molygen 5W-40")

    def test_product_of_selected_region(self):
        response = self.visitor(self.mary).get(reverse("cart:product_detail", args=[self.product.slug]))
        self.assertContains(response, "260.00")

    def test_region_order_of_home_blocks(self):
        html = self.visitor(self.ashgabat).get(reverse("cart:home")).content.decode()
        self.assertLess(html.index('class="home-hero"'), html.index('class="home-cats"'))
        self.assertLess(html.index('class="home-cats"'), html.index('class="home-products"'))

    def test_default_banners_when_region_has_none(self):
        html = self.visitor(self.ashgabat).get(reverse("cart:home")).content.decode()
        self.assertIn("motor-oils-desktop", html)

    def test_scripts_are_rendered_once(self):
        html = self.visitor(self.ashgabat).get(reverse("cart:home")).content.decode()
        self.assertEqual(html.count("js/shop.js"), 1)
        self.assertNotIn("leaflet", html)

    def test_search_pagination_keeps_query(self):
        for i in range(60):
            Product.objects.create(place=self.ashgabat, category=self.oils, title_tm=f"Moly {i}", slug=f"moly-{i}")
        html = self.visitor(self.ashgabat).get(reverse("cart:search-item") + "?query=moly").content.decode()
        self.assertIn("query=moly&amp;page=2", html)

    def test_duplicate_category_slug_does_not_500(self):
        Category.objects.create(title_tm="Motor ýaglary", slug=self.oils.slug)
        response = self.visitor().get(reverse("cart:category-detail", args=[self.oils.slug]))
        self.assertEqual(response.status_code, 200)

    def test_unknown_category_is_404(self):
        self.assertEqual(self.visitor().get(reverse("cart:category-detail", args=["nope"])).status_code, 404)


class CartSecurityTests(ShopTestCase):
    def add(self, client, product):
        return client.post(reverse("cart:add-to-cart"), {"product_id": product.pk})

    def test_add_and_count(self):
        client = self.visitor(self.ashgabat)
        response = self.add(client, self.product)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(CartItem.objects.count(), 1)

    def test_cannot_touch_someone_elses_cart_item(self):
        owner = self.visitor(self.ashgabat)
        self.add(owner, self.product)
        item = CartItem.objects.get()

        attacker = self.visitor(self.ashgabat)
        attacker.get(reverse("cart:home"))  # gets its own device_id
        ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
        for name in ("cart:increase-quantity", "cart:decrease-quantity", "cart:remove-from-cart"):
            with self.subTest(view=name):
                response = attacker.post(reverse(name), {"id": item.pk}, **ajax)
                self.assertEqual(response.status_code, 404)

        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)

    def test_owner_can_change_own_item(self):
        client = self.visitor(self.ashgabat)
        self.add(client, self.product)
        item = CartItem.objects.get()
        ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
        response = client.post(reverse("cart:increase-quantity"), {"id": item.pk}, **ajax)
        self.assertEqual(response.json()["quantity"], 2)
        client.post(reverse("cart:remove-from-cart"), {"id": item.pk}, **ajax)
        self.assertFalse(CartItem.objects.exists())

    def test_bad_input_is_rejected_not_500(self):
        client = self.visitor(self.ashgabat)
        self.assertEqual(client.post(reverse("cart:add-to-cart"), {"product_id": "x"}).status_code, 400)
        self.assertEqual(client.post(reverse("cart:add-to-cart"), {"product_id": "999999"}).status_code, 404)
        self.assertEqual(client.post(reverse("cart:get-by-brand"), {"brand_id": "x"}).status_code, 200)
        self.assertEqual(client.post(reverse("cart:get-by-brand"), {"brand_id": "999"}).json(), [])
        self.assertEqual(client.post(reverse("cart:set_place"), {"place_id": "999"}).status_code, 400)

    def test_long_car_params_are_clipped(self):
        client = self.visitor(self.ashgabat)
        product = Product.objects.create(place=self.ashgabat, category=self.params_cat, title_tm="Service", slug="svc")
        client.post(
            reverse("cart:add-to-cart"),
            {"product_id": product.pk, "car_number": "A" * 100, "engine": "1.6 turbo diesel"},
        )
        item = CartItem.objects.get()
        self.assertEqual(len(item.license_plate), 20)
        self.assertEqual(len(item.engine), 10)

    def test_models_endpoint(self):
        toyota = Brand.objects.create(place=self.ashgabat, title="Toyota", type="brand")
        Brand.objects.create(place=self.ashgabat, title="Camry", type="model", parent=toyota)
        data = self.client.post(reverse("cart:get-by-brand"), {"brand_id": toyota.pk}).json()
        self.assertEqual([d["title"] for d in data], ["Camry"])


class CheckoutTests(ShopTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(phone_number="61234567", password="secret123", place=self.ashgabat)

    def login(self, client):
        client.post(reverse("users:login"), {"phone_number": "61234567", "password": "secret123"})

    def test_same_product_for_two_cars_can_be_ordered(self):
        service = Product.objects.create(
            place=self.ashgabat, category=self.params_cat, title_tm="Service", slug="svc", price=Decimal("10")
        )
        client = self.visitor(self.ashgabat)
        self.login(client)
        for plate in ("DB1234AG", "AB1234MR"):
            client.post(reverse("cart:add-to-cart"), {"product_id": service.pk, "car_number": plate, "brand": "Toyota"})
        self.assertEqual(CartItem.objects.filter(user=self.user).count(), 2)

        client.post(reverse("cart:checkout-order"))
        order = Order.objects.get()
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.total_price, Decimal("20.00"))
        self.assertEqual(order.place, self.ashgabat)
        self.assertFalse(CartItem.objects.exists())

    def test_guest_cart_moves_to_account_on_login(self):
        client = self.visitor(self.ashgabat)
        client.post(reverse("cart:add-to-cart"), {"product_id": self.product.pk})
        self.login(client)
        self.assertEqual(CartItem.objects.get().user, self.user)

    def test_checkout_requires_login(self):
        client = self.visitor(self.ashgabat)
        client.post(reverse("cart:add-to-cart"), {"product_id": self.product.pk})
        client.post(reverse("cart:checkout-order"))
        self.assertFalse(Order.objects.exists())


class ReviewTests(ShopTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(phone_number="61234567", password="secret123")
        self.client.force_login(self.user)

    def test_star_must_be_1_to_5(self):
        self.client.post(reverse("cart:add-review"), {"r_rating": "1000", "r_comment": "x"})
        self.client.post(
            reverse("cart:add-review-product"),
            {"rating_star_product": "-3", "product_id": self.product.pk},
        )
        self.assertFalse(Rating.objects.exists())

        self.client.post(reverse("cart:add-review"), {"r_rating": "5", "r_comment": "Gowy"})
        self.assertEqual(Rating.objects.get().star, 5)


class ThumbnailTests(ShopTestCase):
    def test_thumbnail_generated_and_used(self):
        self.product.image = SimpleUploadedFile("big.png", png_bytes(), content_type="image/png")
        self.product.save()

        html = self.visitor(self.ashgabat).get(reverse("cart:product-list")).content.decode()
        self.assertIn("/media/thumbs/480/", html)

        from cart.images import thumbnail_paths

        _, target, _ = thumbnail_paths(self.product.image.name, 480)
        self.assertTrue(target.exists())
        with Image.open(target) as img:
            self.assertEqual(img.format, "WEBP")
            self.assertEqual(img.width, 480)

    def test_missing_file_falls_back_to_original_url(self):
        from cart.images import thumbnail_url

        self.product.image.name = "product_images/does-not-exist.png"
        self.assertTrue(thumbnail_url(self.product.image, 240).endswith("does-not-exist.png"))


class CacheInvalidationTests(ShopTestCase):
    def test_banner_change_visible_immediately(self):
        client = self.visitor(self.ashgabat)
        client.get(reverse("cart:home"))  # warm cache (no banners -> defaults)
        Banner.objects.create(
            place=self.ashgabat,
            title_tm="Täze banner",
            title_ru="Новый баннер",
            description_tm="d",
            description_ru="d",
            image=SimpleUploadedFile("b.png", png_bytes((800, 400)), content_type="image/png"),
        )
        self.assertContains(client.get(reverse("cart:home")), "Täze banner")

    def test_category_change_visible_immediately(self):
        client = self.visitor(self.ashgabat)
        client.get(reverse("cart:home"))
        Category.objects.create(title_tm="Täze kategoriýa")
        self.assertContains(client.get(reverse("cart:home")), "Täze kategoriýa")
