from django import template
from django.core.cache import cache
from django.db.models import Avg, Count
from django.utils.translation import get_language

from cart.images import thumbnail_url
from cart.models import Brand, CartItem, Category, Rating
from cart.services import (
    BRAND_OPTIONS_CACHE_KEY,
    CACHE_TTL,
    CATEGORIES_FOOTER_CACHE_KEY,
    CATEGORIES_MAIN_CACHE_KEY,
    RATING_SUMMARY_CACHE_KEY,
    get_place as _get_place,
    get_places,
)

register = template.Library()


# --------------------------------------------------------------------------
# Catalogue data (cached; invalidated by cart/signals.py)
# --------------------------------------------------------------------------
@register.simple_tag
def categories():
    items = cache.get(CATEGORIES_MAIN_CACHE_KEY)
    if items is None:
        items = list(
            Category.objects.filter(parent__isnull=True)
            .prefetch_related("children")
            .order_by("sort_order", "title_tm", "title_ru")
        )
        cache.set(CATEGORIES_MAIN_CACHE_KEY, items, CACHE_TTL)
    return items


@register.simple_tag
def footer_categories():
    items = cache.get(CATEGORIES_FOOTER_CACHE_KEY)
    if items is None:
        items = list(
            Category.objects.filter(parent__isnull=True)
            .prefetch_related("children")
            .order_by("-created_at")[:3]
        )
        cache.set(CATEGORIES_FOOTER_CACHE_KEY, items, CACHE_TTL)
    return items


@register.simple_tag
def places():
    return get_places()


@register.simple_tag
def get_place(place_id):
    return _get_place(place_id)


@register.simple_tag
def brand_options():
    """Brands grouped by type: {"brand": [(id, title), ...], "yyly": [...], ...}.

    Replaces looping over all ~650 brands six times in every page (which
    produced ~240 KB of whitespace per page)."""
    groups = cache.get(BRAND_OPTIONS_CACHE_KEY)
    if groups is None:
        groups = {}
        for pk, title, type_ in Brand.objects.order_by("title").values_list("id", "title", "type"):
            groups.setdefault(type_ or "", []).append((pk, title))
        cache.set(BRAND_OPTIONS_CACHE_KEY, groups, CACHE_TTL)
    return groups


@register.simple_tag
def get_brands():
    """Kept for backwards compatibility with old templates."""
    brands = cache.get("all_brands")
    if brands is None:
        brands = list(Brand.objects.all())
        cache.set("all_brands", brands, CACHE_TTL)
    return brands


def _rating_summary():
    summary = cache.get(RATING_SUMMARY_CACHE_KEY)
    if summary is None:
        agg = Rating.objects.filter(status="success").aggregate(avg=Avg("star"), count=Count("id"))
        summary = {"avg": round(agg["avg"], 2) if agg["avg"] else 0.0, "count": agg["count"]}
        cache.set(RATING_SUMMARY_CACHE_KEY, summary, CACHE_TTL)
    return summary


@register.simple_tag
def get_ratings(key: str = "all"):
    if key == "avg":
        return _rating_summary()["avg"]
    if key == "count":
        return _rating_summary()["count"]
    qs = Rating.objects.filter(status="success").select_related("user").order_by("-created_at")
    if key == "all":
        return qs
    return qs


# --------------------------------------------------------------------------
# Cart (legacy filters; new templates use cart_count / cart_product_ids
# from the context processor, which query once per request)
# --------------------------------------------------------------------------
def _owner_items(user, device_id):
    if user.is_authenticated:
        return CartItem.objects.filter(user=user)
    return CartItem.objects.filter(device_id=device_id, user__isnull=True)


@register.filter
def get_cart_item_ids(user, device_id):
    return list(_owner_items(user, device_id).values_list("product_id", flat=True))


@register.filter
def get_cart_item_count(user, device_id):
    from django.db.models import Sum

    return _owner_items(user, device_id).aggregate(total=Sum("quantity"))["total"] or 0


# --------------------------------------------------------------------------
# Presentation helpers
# --------------------------------------------------------------------------
@register.filter
def thumb(image_field, width):
    """{{ product.image|thumb:400 }} -> URL of a small WebP version."""
    return thumbnail_url(image_field, width)


@register.simple_tag
def srcset(image_field, *widths):
    """{% srcset product.image 240 480 %} -> "url 240w, url 480w"."""
    if not image_field:
        return ""
    return ", ".join(f"{thumbnail_url(image_field, w)} {w}w" for w in widths)


@register.simple_tag
def tr(obj, field):
    """Localized model field: {% tr product "title" %} -> title_ru for Russian, else title_tm."""
    if obj is None:
        return ""
    get = obj.get if isinstance(obj, dict) else (lambda name, default=None: getattr(obj, name, default))
    if get_language() == "ru":
        value = get(f"{field}_ru", None)
        if value:
            return value
    return get(f"{field}_tm", "") or ""


@register.simple_tag
def banner_static(key, variant):
    """{% banner_static "motor-oils" "mobile.webp" %} -> hashed static URL."""
    from django.templatetags.static import static

    return static(f"images/banners/{key}-{variant}")
