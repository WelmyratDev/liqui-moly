"""Shared helpers for the shop: region (Place) lookup, cart ownership, caching.

Everything that several views / template tags need lives here so the rules are
defined exactly once.
"""
from django.core.cache import cache
from django.db.models import Q, Sum

CACHE_TTL = 60 * 60 * 24  # 1 day; entries are also invalidated on save (signals.py)

PLACES_CACHE_KEY = "all_places"
BRAND_OPTIONS_CACHE_KEY = "brand_options_v2"
CATEGORIES_MAIN_CACHE_KEY = "categories_main"
CATEGORIES_FOOTER_CACHE_KEY = "categories_footer"
RATING_SUMMARY_CACHE_KEY = "rating_summary"

MAX_CART_ITEM_QUANTITY = 99


def banners_cache_key(place_id):
    return f"banners_place_{place_id}"


def brand_children_cache_key(brand_id):
    return f"brand_children_{brand_id}"


# --------------------------------------------------------------------------
# Places (regions)
# --------------------------------------------------------------------------
def get_places():
    """All places, cached.  Small table (6 rows)."""
    from .models import Place

    places = cache.get(PLACES_CACHE_KEY)
    if places is None:
        places = list(Place.objects.order_by("id"))
        cache.set(PLACES_CACHE_KEY, places, CACHE_TTL)
    return places


def get_place(place_id):
    """Return the Place for an id (int or str) or None; never raises."""
    try:
        place_id = int(place_id)
    except (TypeError, ValueError):
        return None
    for place in get_places():
        if place.pk == place_id:
            return place
    return None


def default_place():
    """Place used for browsing before the visitor picked a region
    (search engines, first visit).  The region modal still asks the visitor."""
    places = get_places()
    return places[0] if places else None


def catalog_place_id(request):
    """Region whose catalogue should be shown for this request."""
    if getattr(request, "place", None) is not None:
        return request.place.pk
    place = default_place()
    return place.pk if place else None


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# Cart ownership
# --------------------------------------------------------------------------
def cart_owner_filter(request):
    """Q() matching exactly the cart items that belong to the current visitor.

    Logged in  -> items of the user.
    Anonymous  -> items of this browser (device_id) not attached to any user.
    """
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return Q(user=user)
    return Q(device_id=getattr(request, "device_id", None), user__isnull=True)


def cart_items_for(request):
    from .models import CartItem

    return CartItem.objects.filter(cart_owner_filter(request))


def cart_total_quantity(request):
    return cart_items_for(request).aggregate(total=Sum("quantity"))["total"] or 0
