from django.core.validators import MaxValueValidator, MinValueValidator
from django.conf import settings
from django.db import models
from django.db.models.aggregates import Avg
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from users.models import User
from django.utils.text import slugify
from django.urls import reverse
import os
import secrets


class Place(models.Model):
    title_tm = models.CharField(verbose_name=_('Title Tm'))
    title_ru = models.CharField(verbose_name=_('Title Ru'), blank=True, null=True)
    google_maps_url = models.TextField(blank=True, null=True, verbose_name="Google Maps Embed URL")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title_tm
    
    class Meta:
        verbose_name = _("Place")
        verbose_name_plural = _("Places")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete("all_places")


    def delete(self, *args, **kwargs):
        cache.delete("all_places")
        super().delete(*args, **kwargs)

class Banner(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, verbose_name=_('Place'))
    title_tm = models.CharField(max_length=150, verbose_name=_('title_tm'))
    title_ru = models.CharField(max_length=150, verbose_name=_('title_ru'))
    image = models.ImageField(verbose_name=_('Image'), upload_to='slider_images')
    image_sm = models.ImageField(verbose_name=_('Image Small'), upload_to='slider_images_sm', blank=True, null=True)
    description_tm = models.TextField(verbose_name=_('Description Tm'))
    description_ru = models.TextField(verbose_name=_('Description Ru'))
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title_tm
    
    class Meta:
        verbose_name = _("Banner")
        verbose_name_plural = _("Banners")


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image:
            ext = self.image.name.split(".")[-1]

            new_name = f"slider_images/{self.pk}.{ext}"

            if self.image.name != new_name:
                new_path = os.path.join(
                    settings.MEDIA_ROOT,
                    new_name
                )

                os.makedirs(
                    os.path.dirname(new_path),
                    exist_ok=True
                )

                if os.path.exists(self.image.path):
                    os.rename(
                        self.image.path,
                        new_path
                    )

                    self.image.name = new_name

                    super().save(
                        update_fields=["image"]
                    )

        if self.image_sm:
            ext = self.image_sm.name.split(".")[-1]

            new_name = f"slider_images_sm/{self.pk}.{ext}"

            if self.image_sm.name != new_name:
                new_path = os.path.join(
                    settings.MEDIA_ROOT,
                    new_name
                )

                os.makedirs(
                    os.path.dirname(new_path),
                    exist_ok=True
                )

                if os.path.exists(self.image_sm.path):
                    os.rename(
                        self.image_sm.path,
                        new_path
                    )

                    self.image_sm.name = new_name

                    super().save(
                        update_fields=["image_sm"]
                    )


class Brand(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, verbose_name=_('Place'))
    title = models.CharField(max_length=200)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, blank=True, null=True, related_name="children", verbose_name=_("Parent"))
    type = models.CharField(max_length=200, verbose_name=_("type"), blank=True, null=True)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = _("Brand")
        verbose_name_plural = _("Brands")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete("all_brands")


    def delete(self, *args, **kwargs):
        cache.delete("all_brands")
        super().delete(*args, **kwargs)


class Category(models.Model):

    title_tm = models.CharField(
        max_length=200,
        verbose_name=_("Title TM")
    )

    title_ru = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Title RU")
    )

    image = models.ImageField(
        upload_to="category_images",
        blank=True,
        null=True,
        verbose_name=_("Image")
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        blank=True,
        null=True,
        verbose_name=_("Parent Category")
    )

    slug = models.SlugField(
        max_length=400,
        verbose_name=_("Slug"),
        blank=True,
        null=True,
        allow_unicode=True
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Sort Order")
    )

    requires_parameters = models.BooleanField(
        default=False,
        verbose_name=_("Requires Parameters")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['sort_order', 'title_tm', 'title_ru']

    def __str__(self):
        return self.title_tm
    

    @property
    def has_children(self):
        return self.children.exists()

    def get_absolute_url(self):
        return reverse("cart:category-detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(
                self.title_tm,
                allow_unicode=True
            )

        super().save(*args, **kwargs)

        if self.image:
            ext = self.image.name.split(".")[-1]

            new_name = f"category_images/{self.pk}.{ext}"

            if self.image.name != new_name:
                new_path = os.path.join(
                    settings.MEDIA_ROOT,
                    new_name
                )

                os.makedirs(
                    os.path.dirname(new_path),
                    exist_ok=True
                )

                if os.path.exists(self.image.path):
                    os.rename(
                        self.image.path,
                        new_path
                    )

                    self.image.name = new_name

                    super().save(
                        update_fields=["image"]
                    )

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


def get_product_image_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    
    place_slug = str(instance.place.title_tm).lower() if (instance.place and hasattr(instance.place, 'title_tm')) else 'default'
    if instance.slug:
        file_name = instance.slug
    elif instance.title_tm:
        file_name = slugify(instance.title_tm, allow_unicode=True)
    else:
        file_name = 'product'

    new_filename = f"{file_name}.{ext}"
    return os.path.join('product_images', place_slug, new_filename)


class Product(models.Model):
    place = models.ForeignKey(
        Place,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name=_("Place")
    )

    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name="products",
        verbose_name=_('Category')
    )

    title_tm = models.CharField(
        max_length=200,
        verbose_name=_("Title TM")
    )

    title_ru = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Title RU")
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Price")
    )

    image = models.ImageField(
        upload_to=get_product_image_path, 
        blank=True,
        null=True,
        verbose_name=_("Image")
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description")
    )

    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantity")
    )

    slug = models.SlugField(
        max_length=255,
        verbose_name=_("Slug"),
        blank=True,
        null=True,
        allow_unicode=True
    )

    seo_title = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    seo_description = models.TextField(
        blank=True,
        null=True
    )

    seo_keywords = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    is_top = models.BooleanField(default=False)

    updated_at = models.DateField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return self.title_tm

    def get_absolute_url(self):
        return reverse("cart:product_detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(
                self.title_tm,
                allow_unicode=True
            )
    
        super().save(*args, **kwargs)


class Specification(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="specifications",
        verbose_name=_("Product")
    )

    key_tm = models.CharField(
        max_length=200,
        verbose_name=_("Key TM")
    )

    key_ru = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Key RU")
    )

    value_tm = models.CharField(
        max_length=200,
        verbose_name=_("Value TM")
    )

    value_ru = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Value RU")
    )

    class Meta:
        verbose_name = _("Specification")
        verbose_name_plural = _("Specifications")

    def __str__(self):
        return f"{self.key_tm}: {self.value_tm}"
    


class CartItem(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name=_("Product")
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="cart_items",
        blank=True,
        null=True,
        verbose_name=_("User")
    )

    device_id = models.CharField(
        max_length=255,
        verbose_name=_("Device ID")
    )

    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantity")
    )

    brand = models.CharField(
        max_length=100,
        verbose_name=_("Brand"),
        blank=True,
        null=True
    )

    model = models.CharField(
        max_length=100,
        verbose_name=_("Model"),
        blank=True,
        null=True
    )

    year = models.CharField(
        max_length=100,
        verbose_name=_("Year"),
        blank=True,
        null=True
    )

    engine = models.CharField(
        max_length=10,
        verbose_name=_("Engine"),
        blank=True,
        null=True
    )

    casting_type = models.CharField(
        max_length=100,
        verbose_name=_("Casting Type"),
        blank=True,
        null=True
    )
    
    car_number_type = models.CharField(
        max_length=100,
        verbose_name=_("Car Number Type"),
        blank=True,
        null=True
    )

    license_plate = models.CharField(
        max_length=20,
        verbose_name=_("Car Number"),
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )

    class Meta:
        verbose_name = _("Cart Item")
        verbose_name_plural = _("Cart Items")

    def __str__(self):
        return f"{self.product.title_tm} - {self.quantity}"
    

    def total_price(self):
        return self.product.price * self.quantity
    

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', _('pending')),
        ('success', _('success')),
        ('reject', _('reject'))
    ]

    place = models.ForeignKey(
        Place,
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders",
        verbose_name=_("Place")
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("User")
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name=_("Status")
    )

    address = models.TextField(
        verbose_name=_("Address")
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Total Price")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    def __str__(self):
        return f"Order #{self.id}"
    


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Order")
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Product")
    )

    product_title = models.CharField(
        max_length=255,
        verbose_name=_("Product Title")
    )

    product_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Product Price")
    )

    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantity")
    )

    brand = models.CharField(
        max_length=100,
        verbose_name=_("Brand"),
        blank=True,
        null=True
    )

    model = models.CharField(
        max_length=100,
        verbose_name=_("Model"),
        blank=True,
        null=True
    )

    year = models.CharField(
        max_length=100,
        verbose_name=_("Year"),
        blank=True,
        null=True
    )

    engine = models.CharField(
        max_length=10,
        verbose_name=_("Engine"),
        blank=True,
        null=True
    )

    casting_type = models.CharField(
        max_length=100,
        verbose_name=_("Casting Type"),
        blank=True,
        null=True
    )
    
    car_number_type = models.CharField(
        max_length=100,
        verbose_name=_("Car Number Type"),
        blank=True,
        null=True
    )

    license_plate = models.CharField(
        max_length=20,
        verbose_name=_("Car Number"),
        blank=True,
        null=True
    )

    def get_total(self):
        if not self.product_price:
            return 0
        return self.product_price * (self.quantity or 0)

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")
        # NOTE: the old unique (order, product) constraint was removed: the same
        # product can legitimately be ordered for two different cars.

    def __str__(self):
        return f"{self.product_title} x {self.quantity}"


class Rating(models.Model):
    STATUS_CHOICES = [
        ('pending', _('pending')),
        ('success', _('success')),
        ('reject', _('reject'))
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    star = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=8, choices=STATUS_CHOICES)

    def __str__(self):
        return f"Rating {self.id}"


    @classmethod
    def get_average_rating(cls):
        avg = cls.objects.filter(status="success").aggregate(Avg('star'))['star__avg']
        return round(avg, 2) if avg else 0
