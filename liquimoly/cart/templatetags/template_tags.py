from django import template
from cart.models import Category, CartItem, Place, Brand, Rating
from django.db.models import Avg, Sum
from django.core.cache import cache


register = template.Library()

@register.simple_tag
def categories():
    cache_key = "categories_main"

    categories = cache.get(cache_key)

    if categories is None:
        categories = list(
            Category.objects
            .filter(parent__isnull=True)
            .prefetch_related("children")
            .order_by('sort_order', 'title_tm', 'title_ru')
        )

        cache.set(
            cache_key,
            categories,
            60 * 60 * 24 * 30
        )

    return categories


@register.simple_tag
def footer_categories():
    cache_key = "categories_footer"

    categories = cache.get(cache_key)

    if categories is None:
        categories = list(
            Category.objects
            .filter(parent__isnull=True)
            .prefetch_related("children")
            .order_by("-created_at")[:3]
        )

        cache.set(
            cache_key,
            categories,
            60 * 60 * 24 * 30
        )

    return categories


@register.simple_tag
def places():
    cache_key = "all_places"

    places = cache.get(cache_key)

    if places is None:
        places = list(Place.objects.all())

        cache.set(
            cache_key,
            places,
            60 * 60 * 24 * 30  # Cache for 30 days
        )

    return places


@register.simple_tag
def get_place(place_id):
    if not place_id:
        return None
    try:
        return Place.objects.filter(pk=place_id).first()
    except (ValueError, TypeError):
        return None

@register.filter
def get_cart_item_ids(user, device_id):
    if user.is_authenticated:
        cart_items = CartItem.objects.filter(user=user)
    else:
        cart_items = CartItem.objects.filter(device_id=device_id)

    return list(cart_items.values_list("product_id", flat=True))



@register.filter
def get_cart_item_count(user, device_id):
    if user.is_authenticated:
        cart_items = CartItem.objects.filter(user=user)
    else:
        cart_items = CartItem.objects.filter(device_id=device_id)

    total = cart_items.aggregate(
        total=Sum("quantity")
    )["total"] or 0
    return total



@register.simple_tag
def get_brands():
    cache_key = "all_brands"

    brands = cache.get(cache_key)

    if brands is None:
        brands = list(Brand.objects.all())

        cache.set(
            cache_key,
            brands,
            60 * 60 * 24 * 30  # Cache for 30 days
        )
    return brands

@register.simple_tag
def get_ratings(key: str = 'all'):
    qs = Rating.objects.filter(status="success")
    
    if key == 'avg':
        result = qs.aggregate(Avg('star'))['star__avg']
        return round(result, 2) if result else 0.0
        
    elif key == 'all':
        return qs.select_related('user').order_by("-created_at")
        
    elif key == 'count':
        return qs.count()

    return qs.order_by("-created_at")
