from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from cart.models import Category, Order, Place, Product
from users.models import User

TEST_SETTINGS = dict(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
    SECURE_SSL_REDIRECT=False,
)


@override_settings(**TEST_SETTINGS)
class LoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.place = Place.objects.create(title_tm="Ashgabat")

    def post(self, client=None, **data):
        client = client or Client()
        return client.post(reverse("users:login"), data)

    def test_first_login_creates_account(self):
        self.post(phone_number="61 23-45-67", password="secret123", fullname="Aman")
        user = User.objects.get()
        self.assertEqual(user.phone_number, "61234567")
        self.assertEqual(user.name, "Aman")

    def test_country_code_is_accepted(self):
        User.objects.create_user(phone_number="61234567", password="secret123")
        client = Client()
        self.post(client, phone_number="+99361234567", password="secret123")
        self.assertIn("_auth_user_id", client.session)

    def test_short_password_rejected_for_new_account(self):
        self.post(phone_number="61234567", password="123")
        self.assertFalse(User.objects.exists())

    def test_wrong_password(self):
        User.objects.create_user(phone_number="61234567", password="secret123")
        client = Client()
        self.post(client, phone_number="61234567", password="nope-nope")
        self.assertNotIn("_auth_user_id", client.session)

    def test_open_redirect_blocked(self):
        response = self.post(phone_number="61234567", password="secret123", next="https://evil.example/")
        self.assertEqual(response["Location"], "/")
        response = self.post(phone_number="61234567", password="secret123", next="/tk/cart/")
        self.assertEqual(response["Location"], "/tk/cart/")

    @override_settings(LOGIN_RATE_LIMIT_ATTEMPTS=3)
    def test_brute_force_is_rate_limited(self):
        User.objects.create_user(phone_number="61234567", password="secret123")
        for _ in range(3):
            self.post(phone_number="61234567", password="wrong-pass")
        client = Client()
        self.post(client, phone_number="61234567", password="secret123")
        self.assertNotIn("_auth_user_id", client.session)

    def test_get_login_redirects_home(self):
        self.assertEqual(Client().get(reverse("users:login")).status_code, 302)


@override_settings(**TEST_SETTINGS)
class ManagerPermissionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.ashgabat = Place.objects.create(title_tm="Ashgabat")
        self.mary = Place.objects.create(title_tm="Mary")
        self.category = Category.objects.create(title_tm="Ýaglar")
        self.own = Product.objects.create(place=self.ashgabat, category=self.category, title_tm="Own")
        self.foreign = Product.objects.create(place=self.mary, category=self.category, title_tm="Foreign")
        self.manager = User.objects.create_user(
            phone_number="65000000", password="secret123", is_staff=True, is_manager=True, place=self.ashgabat
        )
        self.admin = User.objects.create_superuser(phone_number="99300000000", password="secret123", place=self.ashgabat)
        self.client = Client()
        self.client.force_login(self.manager)

    def admin_url(self, name, *args):
        return reverse(f"admin:{name}", args=args)

    def test_manager_cannot_delete_regions_or_categories(self):
        self.assertFalse(self.manager.has_perm("cart.delete_place"))
        self.assertFalse(self.manager.has_perm("cart.delete_category"))
        self.assertFalse(self.manager.has_perm("auth.change_group"))
        self.assertEqual(self.client.get(self.admin_url("cart_place_changelist")).status_code, 403)
        self.assertEqual(self.client.post(self.admin_url("cart_place_delete", self.mary.pk), {"post": "yes"}).status_code, 403)
        self.assertTrue(Place.objects.filter(pk=self.mary.pk).exists())

    def test_manager_sees_only_own_region_products(self):
        response = self.client.get(self.admin_url("cart_product_changelist"))
        self.assertContains(response, "Own")
        self.assertNotContains(response, "Foreign")
        self.assertEqual(self.client.get(self.admin_url("cart_product_change", self.foreign.pk)).status_code, 302)

    def test_manager_cannot_import_products(self):
        self.assertEqual(self.client.get(self.admin_url("cart_product_import")).status_code, 403)

    def test_manager_cannot_edit_superuser(self):
        response = self.client.get(self.admin_url("users_user_change", self.admin.pk))
        self.assertNotEqual(response.status_code, 200)
        response = self.client.get(self.admin_url("auth_user_password_change", self.admin.pk))
        self.assertNotEqual(response.status_code, 200)

    def test_manager_order_list_scoped(self):
        Order.objects.create(place=self.mary, status="success", address="x")
        response = self.client.get(self.admin_url("cart_order_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0 ")

    def test_superuser_still_has_everything(self):
        client = Client()
        client.force_login(self.admin)
        for name in ("cart_place_changelist", "cart_product_changelist", "cart_category_changelist", "users_user_changelist"):
            with self.subTest(name=name):
                self.assertEqual(client.get(self.admin_url(name)).status_code, 200)
