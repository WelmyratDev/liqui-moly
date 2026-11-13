from pyexpat.errors import messages

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportModelAdmin
from django.core.exceptions import ValidationError
from django import forms

from .resources import ProductResource
from .models import Category, Product, Specification, CartItem, OrderItem, Order, Place, Banner, Brand, Rating
from django.urls import path
from django.core.cache import cache


class RatingAdminForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = '__all__'

    def clean_star(self):
        star = self.cleaned_data.get('star', 0)
        
        if star is None:
            star = 0

        if star < 0 or star > 5:
            raise ValidationError('Значение рейтинга (star) должно быть от 0 до 5.')
            
        return star

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    form = RatingAdminForm
    
    list_display = (
        'user',
        'product',
        'star_display',
        'status',
        'created_at',
    )

    list_filter = (
        'status',
        'created_at',
    )

    search_fields = (
        'user__phone_number',
        'product__title_tm',
        'product__title_ru',
    )

    raw_id_fields = (
        'user',
        'product',
    )

    list_per_page = 50

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

    @admin.display(
        description='Rating',
        ordering='star',
    )
    def star_display(self, obj):
        stars = ''.join(
            '<i class="fa-solid fa-star" style="color: #ffd700;"></i>'
            if i <= obj.star
            else '<i class="fa-regular fa-star" style="color: #ffd700;"></i>'
            for i in range(1, 6)
        )

        return format_html(
            '<span style="font-size: 13px; letter-spacing: 2px;">{}</span>',
            format_html(stars),
        )



@admin.register(Brand)
class BrandAdmin(ImportExportModelAdmin):
    list_display = ['place', 'title', 'parent', 'type']
    list_filter = ['type']
    list_display_links = (
        'title',
        'place',
    )
    search_fields = (
        'place__title',
        'title'
    )
    raw_id_fields = ('place', 'parent',)
    list_per_page = 50

    def get_queryset(self, request):

        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(
            place=request.user.place
        )
    
    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['img', 'img_sm', 'place', 'title_tm', 'title_ru', 'created_at']
    raw_id_fields = ('place',)
    list_display_links = (
        'img',
        'img_sm',
    )


    def img(self, obj):
        if obj.image:
            return mark_safe(f'<img src={obj.image.url} width=100>')
        return None

    def img_sm(self, obj):
        if obj.image_sm:
            return mark_safe(f'<img src={obj.image_sm.url} width=100>')
        return None
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'clear-region-cache/', 
                self.admin_site.admin_view(self.clear_region_cache_view), 
                name='banner_clear_region_cache'
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['places'] = Place.objects.all()
        return super().changelist_view(request, extra_context=extra_context)

    def clear_region_cache_view(self, request):
        if request.method == 'POST':
            place_id = request.POST.get('place_id')
            
            if place_id == 'all':
                places = Place.objects.all()
                for p in places:
                    cache.delete(f"banners_place_{p.id}")
                self.message_user(request, "Кеш баннеров для ВСЕХ регионов очищен!", level="success")
            
            elif place_id:
                cache.delete(f"banners_place_{place_id}")
                try:
                    place = Place.objects.get(id=place_id)
                    self.message_user(request, f"Кеш баннеров для региона '{place}' очищен!", level="success")
                except Place.DoesNotExist:
                    pass
            else:
                self.message_user(request, "Вы не выбрали регион для очистки!", level="warning")

        return HttpResponseRedirect("../")
    
    def get_queryset(self, request):

        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(
            place=request.user.place
        )


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title_tm',
        'title_ru',
        'created_at',
    )
    list_display_links = (
        'id',
        'title_tm'
    )
    search_fields = (
        'title_tm',
        'title_ru',
    )
    list_filter = (
        'created_at',
    )
    ordering = (
        '-created_at',
    )
    readonly_fields = (
        'created_at',
    )
    
    def has_module_permission(self, request):
        return request.user.is_superuser


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        'image_preview',
        'title_tm',
        'title_ru',
        'sort_order',
        'parent',
        'created_at',
    )

    list_editable = ['sort_order']

    list_display_links = (
        'image_preview',
        'title_tm',
    )

    list_per_page = 50

    raw_id_fields = ('parent',)

    search_fields = (
        'title_tm',
        'title_ru',
    )

    list_filter = (
        'created_at',
        'parent',
    )

    readonly_fields = (
        'created_at',
        'image_preview',
    )

    autocomplete_fields = (
        'parent',
    )

    ordering = (
        '-created_at',
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'clear-cache/', 
                self.admin_site.admin_view(self.clear_cache_view), 
                name='category_clear_cache'
            ),
        ]
        return custom_urls + urls

    def clear_cache_view(self, request):
        cache.delete("categories_main")
        cache.delete("categories_footer")
      
        self.message_user(request, "Кеш категорий успешно очищен!", level="success")
        
        return HttpResponseRedirect("../")

    def image_preview(self, obj):

        if obj.image:
            return format_html(
                '<img src="{}" width="70" height="70" style="border-radius:10px; object-fit:cover;" />',
                obj.image.url
            )

        return "-"

    image_preview.short_description = _('Preview')


class SpecificationInline(admin.TabularInline):
    model = Specification
    extra = 1
    fields = (
        "key_tm",
        "value_tm",
        "key_ru",
        "value_ru",
    )

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource

    list_display = (
        'image_preview',
        'title_tm',
        'formatted_price',
        'formatted_quantity',
        'is_top',
        'updated_at',
        'created_at',
    )

    inlines = [SpecificationInline]

    list_display_links = (
        'image_preview',
        'title_tm',
    )

    list_per_page = 50

    raw_id_fields = ('category', 'place',)

    search_fields = (
        'title_tm',
        'title_ru',
        'description',
    )

    list_filter = (
        'created_at',
        'updated_at',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
        'image_preview',
    )

    ordering = (
        '-is_top',
        '-created_at',
    )


    def formatted_price(self, obj):
        return f"{obj.price} TMT"
    
    def formatted_quantity(self, obj):
        return f"{obj.quantity}"

    formatted_price.short_description = _('Price')
    formatted_quantity.short_description = _('Stock Quantity')

    def image_preview(self, obj):

        if obj.image:
            return format_html(
                '<img src="{}" width="70" height="70" style="border-radius:10px; object-fit:contain;" />',
                obj.image.url
            )

        return "-"
    

    def get_list_filter(self, request):
        filters = ['is_top']

        if request.user.is_superuser:
            filters.append('place')

        return filters
    
    def get_queryset(self, request):

        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(
            place=request.user.place
        )


    def has_view_permission(self, request, obj=None):

        if request.user.is_superuser:
            return True

        if obj is None:
            return True

        return obj.place == request.user.place


    def has_change_permission(self, request, obj=None):

        if request.user.is_superuser:
            return True

        if obj is None:
            return True

        return obj.place == request.user.place


    def has_delete_permission(self, request, obj=None):

        if request.user.is_superuser:
            return True

        if obj is None:
            return True

        return obj.place == request.user.place

    image_preview.short_description = _('Preview')


@admin.register(Specification)
class SpecificationAdmin(admin.ModelAdmin):

    list_display = (
        'product',
        'key_tm',
        'key_ru',
        'value_tm',
        'value_ru',
    )

    raw_id_fields = ('product',)

    list_display_links = (
        'product',
    )

    list_per_page = 50

    def get_queryset(self, request):

        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(
            product__place=request.user.place
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "product" and not request.user.is_superuser:

            kwargs["queryset"] = Product.objects.filter(
                place=request.user.place
            )

        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):

    list_display = (
        'product',
        'user',
    )

    raw_id_fields = ('product', 'user')

    list_display_links = (
        'product',
        'user',
    )

    list_per_page = 50

    def get_queryset(self, request):

        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(
            product__place=request.user.place
        )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_image', "product", "product_title", "product_price", "quantity", "get_total")
    can_delete = False

    def product_image(self, obj):
        if obj.product.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:contain; border-radius:5px;" />', obj.product.image.url)
        return "-"

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_title", "quantity", "product_price")
    search_fields = ("product_title", "order__id")
    list_filter = ("order",)
    list_per_page = 50
    raw_id_fields = ('order', 'product',)


    def get_queryset(self, request):

        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(
            order__place=request.user.place
        )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total_price", "status", 'address', "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "user__phone_number")
    readonly_fields = ("total_price", "created_at", "updated_at")
    list_per_page = 50
    raw_id_fields = ('user', 'place',)

    inlines = [OrderItemInline]

    def get_queryset(self, request):

        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(
            place=request.user.place
        )
    
    def has_view_permission(self, request, obj=None):

        if request.user.is_superuser:
            return True

        if obj is None:
            return True

        return obj.place == request.user.place


    def has_change_permission(self, request, obj=None):

        if request.user.is_superuser:
            return True

        if obj is None:
            return True

        return obj.place == request.user.place


    def has_delete_permission(self, request, obj=None):

        if request.user.is_superuser:
            return True

        if obj is None:
            return True

        return obj.place == request.user.place

