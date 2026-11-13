from django import forms
from django.contrib import admin
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin

from .models import Banner, Brand, CartItem, Category, Order, OrderItem, Place, Product, Rating, Specification
from .resources import ProductResource
from .services import CATEGORIES_FOOTER_CACHE_KEY, CATEGORIES_MAIN_CACHE_KEY, banners_cache_key


class PlaceScopedAdminMixin:
    """Regional managers (non-superusers) only see / edit objects of their own
    region, cannot move objects to another region, and new objects are always
    created in their region."""

    place_lookup = "place"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if not getattr(request.user, "place_id", None):
            return qs.none()
        return qs.filter(**{self.place_lookup: request.user.place})

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser and self.place_lookup == "place":
            readonly.append("place")
        return readonly

    def _owns(self, request, obj):
        if obj is None or request.user.is_superuser:
            return True
        if self.place_lookup == "place":
            return obj.place_id is not None and obj.place_id == request.user.place_id
        return self.get_queryset(request).filter(pk=obj.pk).exists()

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and self._owns(request, obj)

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and self._owns(request, obj)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and self._owns(request, obj)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and self.place_lookup == "place" and not change:
            obj.place = request.user.place
        super().save_model(request, obj, form, change)


def image_tag(field, size=70, fit="cover"):
    if not field:
        return "-"
    return format_html(
        '<img src="{}" width="{}" height="{}" loading="lazy" '
        'style="border-radius:10px; object-fit:{};" />',
        field.url, size, size, fit,
    )


# --------------------------------------------------------------------------
# Rating
# --------------------------------------------------------------------------
class RatingAdminForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = "__all__"

    def clean_star(self):
        star = self.cleaned_data.get("star", 0)
        if star is None:
            star = 0
        if star < 0 or star > 5:
            raise ValidationError("Значение рейтинга (star) должно быть от 0 до 5.")
        return star


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    form = RatingAdminForm
    list_display = ("user", "product", "star_display", "status", "created_at")
    list_filter = ("status", "created_at")
    list_editable = ()
    search_fields = ("user__phone_number", "product__title_tm", "product__title_ru")
    raw_id_fields = ("user", "product")
    list_select_related = ("user", "product")
    list_per_page = 50
    actions = ["approve", "reject"]

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description="Rating", ordering="star")
    def star_display(self, obj):
        stars = "".join(
            '<i class="fa-solid fa-star" style="color: #ffd700;"></i>'
            if i <= obj.star
            else '<i class="fa-regular fa-star" style="color: #ffd700;"></i>'
            for i in range(1, 6)
        )
        return format_html('<span style="font-size: 13px; letter-spacing: 2px;">{}</span>', format_html(stars))

    @admin.action(description=_("Approve selected reviews"))
    def approve(self, request, queryset):
        for rating in queryset:  # per-object save -> cache signals fire
            rating.status = "success"
            rating.save(update_fields=["status"])

    @admin.action(description=_("Reject selected reviews"))
    def reject(self, request, queryset):
        for rating in queryset:
            rating.status = "reject"
            rating.save(update_fields=["status"])


# --------------------------------------------------------------------------
# Brand / Banner / Place
# --------------------------------------------------------------------------
@admin.register(Brand)
class BrandAdmin(ImportExportModelAdmin):
    list_display = ["place", "title", "parent", "type"]
    list_filter = ["type"]
    list_display_links = ("title", "place")
    search_fields = ("place__title_tm", "title")
    raw_id_fields = ("place", "parent")
    list_select_related = ("place", "parent")
    list_per_page = 50

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(place=request.user.place)

    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(Banner)
class BannerAdmin(PlaceScopedAdminMixin, admin.ModelAdmin):
    list_display = ["img", "img_sm", "place", "title_tm", "title_ru", "created_at"]
    raw_id_fields = ("place",)
    list_display_links = ("img", "img_sm")
    list_select_related = ("place",)

    @admin.display(description=_("Image"))
    def img(self, obj):
        return image_tag(obj.image, 100)

    @admin.display(description=_("Image Small"))
    def img_sm(self, obj):
        return image_tag(obj.image_sm, 100)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "clear-region-cache/",
                self.admin_site.admin_view(self.clear_region_cache_view),
                name="banner_clear_region_cache",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["places"] = Place.objects.all()
        return super().changelist_view(request, extra_context=extra_context)

    def clear_region_cache_view(self, request):
        # The cache is now also cleared automatically on every banner save/delete.
        if request.method == "POST":
            place_id = request.POST.get("place_id")

            if place_id == "all":
                cache.delete_many([banners_cache_key(p.id) for p in Place.objects.all()])
                self.message_user(request, "Кеш баннеров для ВСЕХ регионов очищен!", level="success")
            elif place_id:
                cache.delete(banners_cache_key(place_id))
                place = Place.objects.filter(id=place_id).first() if place_id.isdigit() else None
                if place:
                    self.message_user(request, f"Кеш баннеров для региона '{place}' очищен!", level="success")
            else:
                self.message_user(request, "Вы не выбрали регион для очистки!", level="warning")

        return HttpResponseRedirect("../")


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("id", "title_tm", "title_ru", "created_at")
    list_display_links = ("id", "title_tm")
    search_fields = ("title_tm", "title_ru")
    list_filter = ("created_at",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    def has_module_permission(self, request):
        return request.user.is_superuser


# --------------------------------------------------------------------------
# Category
# --------------------------------------------------------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("image_preview", "title_tm", "title_ru", "sort_order", "parent", "created_at")
    list_editable = ["sort_order"]
    list_display_links = ("image_preview", "title_tm")
    list_per_page = 50
    raw_id_fields = ("parent",)
    search_fields = ("title_tm", "title_ru")
    list_filter = ("created_at", "parent")
    readonly_fields = ("created_at", "image_preview")
    autocomplete_fields = ("parent",)
    ordering = ("-created_at",)
    list_select_related = ("parent",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("clear-cache/", self.admin_site.admin_view(self.clear_cache_view), name="category_clear_cache"),
        ]
        return custom_urls + urls

    def clear_cache_view(self, request):
        cache.delete_many([CATEGORIES_MAIN_CACHE_KEY, CATEGORIES_FOOTER_CACHE_KEY])
        self.message_user(request, "Кеш категорий успешно очищен!", level="success")
        return HttpResponseRedirect("../")

    @admin.display(description=_("Preview"))
    def image_preview(self, obj):
        return image_tag(obj.image, 70)


# --------------------------------------------------------------------------
# Product
# --------------------------------------------------------------------------
class SpecificationInline(admin.TabularInline):
    model = Specification
    extra = 1
    fields = ("key_tm", "value_tm", "key_ru", "value_ru")


@admin.register(Product)
class ProductAdmin(PlaceScopedAdminMixin, ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = (
        "image_preview",
        "title_tm",
        "formatted_price",
        "formatted_quantity",
        "is_top",
        "updated_at",
        "created_at",
    )
    inlines = [SpecificationInline]
    list_display_links = ("image_preview", "title_tm")
    list_per_page = 50
    raw_id_fields = ("category", "place")
    search_fields = ("title_tm", "title_ru", "description")
    readonly_fields = ("created_at", "updated_at", "image_preview")
    ordering = ("-is_top", "-created_at")
    list_select_related = ("place", "category")

    @admin.display(description=_("Price"))
    def formatted_price(self, obj):
        return f"{obj.price} TMT"

    @admin.display(description=_("Stock Quantity"))
    def formatted_quantity(self, obj):
        return f"{obj.quantity}"

    @admin.display(description=_("Preview"))
    def image_preview(self, obj):
        return image_tag(obj.image, 70, "contain")

    def get_list_filter(self, request):
        filters = ["is_top"]
        if request.user.is_superuser:
            filters.append("place")
        return filters

    def has_import_permission(self, request):
        # An import can overwrite any product by id, including other regions'.
        return request.user.is_superuser


@admin.register(Specification)
class SpecificationAdmin(PlaceScopedAdminMixin, admin.ModelAdmin):
    place_lookup = "product__place"
    list_display = ("product", "key_tm", "key_ru", "value_tm", "value_ru")
    raw_id_fields = ("product",)
    list_display_links = ("product",)
    list_select_related = ("product",)
    list_per_page = 50

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "product" and not request.user.is_superuser:
            kwargs["queryset"] = Product.objects.filter(place=request.user.place)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# --------------------------------------------------------------------------
# Cart & orders
# --------------------------------------------------------------------------
@admin.register(CartItem)
class CartItemAdmin(PlaceScopedAdminMixin, admin.ModelAdmin):
    place_lookup = "product__place"
    list_display = ("product", "user", "quantity", "created_at")
    raw_id_fields = ("product", "user")
    list_display_links = ("product", "user")
    list_select_related = ("product", "user")
    list_per_page = 50


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_image", "product", "product_title", "product_price", "quantity", "get_total")
    can_delete = False

    def product_image(self, obj):
        # product is SET_NULL: it may have been deleted since the order was placed
        if obj.product and obj.product.image:
            return format_html(
                '<img src="{}" width="50" height="50" loading="lazy" '
                'style="object-fit:contain; border-radius:5px;" />',
                obj.product.image.url,
            )
        return "-"


@admin.register(OrderItem)
class OrderItemAdmin(PlaceScopedAdminMixin, admin.ModelAdmin):
    place_lookup = "order__place"
    list_display = ("order", "product_title", "quantity", "product_price")
    search_fields = ("product_title", "order__id")
    list_filter = ("order",)
    list_per_page = 50
    raw_id_fields = ("order", "product")
    list_select_related = ("order",)


@admin.register(Order)
class OrderAdmin(PlaceScopedAdminMixin, admin.ModelAdmin):
    list_display = ("id", "user", "total_price", "status", "address", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "user__phone_number")
    readonly_fields = ("total_price", "created_at", "updated_at")
    list_per_page = 50
    raw_id_fields = ("user", "place")
    list_select_related = ("user",)
    inlines = [OrderItemInline]
