import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .ajax import is_ajax
from .default_banners import DEFAULT_BANNERS
from .models import Banner, Brand, CartItem, Category, Order, OrderItem, Product, Rating
from .services import (
    CACHE_TTL,
    MAX_CART_ITEM_QUANTITY,
    banners_cache_key,
    brand_children_cache_key,
    cart_items_for,
    cart_owner_filter,
    cart_total_quantity,
    catalog_place_id,
    get_place,
    parse_int,
)

logger = logging.getLogger(__name__)

PRODUCTS_PER_PAGE = 48  # divisible by 2, 3 and 4 columns -> no half-empty last row


def _safe_referer(request, fallback="/"):
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return referer
    return fallback


def _clip(value, max_length):
    """Trim user input to the DB column size (Postgres errors on overflow)."""
    if value is None:
        return None
    value = str(value).strip()
    return value[:max_length] or None


def _paginate(request, queryset):
    paginator = Paginator(queryset, PRODUCTS_PER_PAGE)
    return paginator.get_page(request.GET.get("page"))


def _catalog_products(request):
    """Products of the visitor's region (or the default region before one is chosen)."""
    place_id = catalog_place_id(request)
    qs = Product.objects.select_related("category")
    if place_id is None:
        return qs.none()
    return qs.filter(place_id=place_id)


# --------------------------------------------------------------------------
# Catalogue pages
# --------------------------------------------------------------------------
def index(request):
    place_id = catalog_place_id(request)

    products = _catalog_products(request).filter(is_top=True).order_by("created_at")[:12]

    banners = None
    if place_id is not None:
        cache_key = banners_cache_key(place_id)
        banners = cache.get(cache_key)
        if banners is None:
            banners = list(Banner.objects.filter(place_id=place_id).order_by("-created_at")[:8])
            cache.set(cache_key, banners, CACHE_TTL)

    return render(
        request,
        "cart/index.html",
        {"products": products, "banners": banners or [], "default_banners": DEFAULT_BANNERS},
    )


def product_detail(request, slug):
    base_qs = Product.objects.select_related("category").filter(slug=slug)

    if request.has_place:
        product = base_qs.filter(place_id=request.place_id).order_by("id").first()
    else:
        # No region chosen yet (search engine, shared link): show the product
        # instead of bouncing to the home page; the region picker still opens.
        product = base_qs.filter(place_id=catalog_place_id(request)).order_by("id").first()
        product = product or base_qs.order_by("id").first()

    if product is None:
        return redirect("cart:home")

    context = {
        "product": product,
        "specifications": product.specifications.order_by("-id"),
    }
    return render(request, "cart/product_detail.html", context)


def category_detail(request, slug):
    category = Category.objects.filter(slug=slug).order_by("id").first()
    if category is None:
        raise Http404("Category not found")

    products = _catalog_products(request).filter(category=category).order_by("id")
    page_obj = _paginate(request, products)

    context = {
        "category": category,
        "products": page_obj,
        "page_obj": page_obj,
        "products_count": page_obj.paginator.count,
    }
    return render(request, "cart/category_detail.html", context)


def product_list(request):
    products = _catalog_products(request).order_by("id")
    page_obj = _paginate(request, products)
    return render(request, "cart/product_list.html", {"products": page_obj, "page_obj": page_obj})


def search_item(request):
    query = request.GET.get("query", "").strip()[:100]

    products = Product.objects.none()
    if query:
        products = (
            _catalog_products(request)
            .filter(Q(title_tm__icontains=query) | Q(title_ru__icontains=query))
            .order_by("id")
        )

    page_obj = _paginate(request, products)
    return render(
        request,
        "cart/search.html",
        {"query": query, "products": page_obj, "page_obj": page_obj},
    )


def about_company(request):
    return render(request, "cart/about_company.html", {})


# --------------------------------------------------------------------------
# Cart
# --------------------------------------------------------------------------
@require_POST
def add_to_cart(request):
    product_id = parse_int(request.POST.get("product_id"))
    if product_id is None:
        return JsonResponse({"status": "error", "error": "invalid product"}, status=400)
    product = get_object_or_404(Product.objects.select_related("category"), id=product_id)

    user = request.user if request.user.is_authenticated else None
    if user:
        owner = {"user": user}
    else:
        owner = {"device_id": request.device_id, "user__isnull": True}

    license_plate = request.POST.get("car_number")
    if license_plate is not None:
        license_plate = license_plate.replace(" ", "").upper()

    params = {
        "brand": _clip(request.POST.get("brand"), 100),
        "model": _clip(request.POST.get("model"), 100),
        "year": _clip(request.POST.get("year"), 100),
        "car_number_type": _clip(request.POST.get("car_number_type"), 100),
        "license_plate": _clip(license_plate, 20),
        "casting_type": _clip(request.POST.get("casting_type"), 100),
        "engine": _clip(request.POST.get("engine"), 10),
    }

    cart_item, created = CartItem.objects.get_or_create(
        product=product,
        defaults={"quantity": 1, "device_id": request.device_id},
        **params,
        **owner,
    )

    return JsonResponse(
        {
            "status": "success",
            "created": created,
            "exists": not created,
            "total": cart_total_quantity(request),
            "item_quantity": cart_item.quantity,
        }
    )


def cart(request):
    cart_items = cart_items_for(request).select_related("product").order_by("created_at")
    return render(request, "cart/cart.html", {"cart_items": cart_items})


def _own_cart_item(request):
    """The visitor's own cart item from POST['id'] - never somebody else's."""
    item_id = parse_int(request.POST.get("id"))
    if item_id is None:
        raise Http404
    return get_object_or_404(CartItem.objects.filter(cart_owner_filter(request)), id=item_id)


def increase_quantity(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)

    cart_item = _own_cart_item(request)
    if cart_item.quantity < MAX_CART_ITEM_QUANTITY:
        CartItem.objects.filter(pk=cart_item.pk).update(quantity=F("quantity") + 1)
        cart_item.refresh_from_db(fields=["quantity"])

    total_count = cart_total_quantity(request)
    if is_ajax(request):
        return JsonResponse({"quantity": cart_item.quantity, "total_count": total_count})
    return JsonResponse({"status": "ok"})


def decrease_quantity(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    cart_item = _own_cart_item(request)
    if cart_item.quantity > 1:
        CartItem.objects.filter(pk=cart_item.pk, quantity__gt=1).update(quantity=F("quantity") - 1)
        cart_item.refresh_from_db(fields=["quantity"])

    if is_ajax(request):
        return JsonResponse(
            {"quantity": cart_item.quantity, "total_count": cart_total_quantity(request)}
        )
    return JsonResponse({"error": "AJAX request required"}, status=400)


def remove_from_cart(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    _own_cart_item(request).delete()

    total_count = cart_total_quantity(request)
    if is_ajax(request):
        return JsonResponse({"total_count": total_count})
    return JsonResponse({"status": "ok", "total_count": total_count})


# --------------------------------------------------------------------------
# Orders
# --------------------------------------------------------------------------
def create_order(request, user=None, status=None):
    """Turn the user's cart into an Order.

    Returns the Order, or one of the legacy error markers used by
    ``checkout_order``: 401 (not logged in), "status", None (empty cart).
    """
    if user is None or not user.is_authenticated:
        return 401

    if not status:
        return "status"

    cart_items = cart_items_for(request).select_related("product")
    if not cart_items.exists():
        return None

    with transaction.atomic():
        order = Order.objects.create(
            place=request.place,
            user=user,
            address="address",
            status=status,
        )

        total = Decimal("0.00")
        order_items = []
        for item in cart_items:
            price = item.product.price or Decimal("0.00")
            order_items.append(
                OrderItem(
                    order=order,
                    product=item.product,
                    product_title=item.product.title_tm,
                    product_price=price,
                    quantity=item.quantity,
                    brand=item.brand,
                    year=item.year,
                    model=item.model,
                    engine=item.engine,
                    casting_type=item.casting_type,
                    car_number_type=item.car_number_type,
                    license_plate=item.license_plate,
                )
            )
            total += price * item.quantity

        OrderItem.objects.bulk_create(order_items)

        order.total_price = total
        order.save(update_fields=["total_price"])

        cart_items.delete()

    logger.info("Order #%s created by user %s (%s items)", order.pk, user.pk, len(order_items))
    return order


def checkout_order(request):
    if request.method != "POST":
        return redirect("cart:cart")

    user = request.user if request.user.is_authenticated else None
    order = create_order(request, user=user, status="success")

    if order is None:
        messages.error(request, "Sebet boş")
    elif order == "status":
        pass
    elif order == 401:
        messages.error(request, "Ulgamyň içine giriň")
    else:
        messages.success(request, "Hyzmat üstünlikli döredildi siz bilen habarlaşylar")

    return redirect("cart:cart")


def orders(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Ulgamyň içine giriň")
        return redirect("/")

    user_orders = request.user.orders.prefetch_related("items").order_by("-created_at")
    return render(request, "cart/orders.html", {"orders": user_orders})


# --------------------------------------------------------------------------
# Region
# --------------------------------------------------------------------------
@require_POST
def set_place(request):
    place = get_place(request.POST.get("place_id"))
    if place is None:
        return JsonResponse({"success": False, "error": "unknown place"}, status=400)

    response = JsonResponse({"success": True})
    response.set_cookie(
        "place_id",
        str(place.pk),
        max_age=60 * 60 * 24 * 30 * 3,  # 3 months
        httponly=False,
        secure=request.is_secure(),
        samesite="Lax",
    )
    return response


@require_POST
def set_location(request):
    next_url = request.POST.get("next_url") or "/"

    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = "/"

    response = redirect(next_url)
    response.delete_cookie("place_id")
    return response


@require_POST
def get_by_brand(request):
    brand_id = parse_int(request.POST.get("brand_id"))
    if brand_id is None:
        return JsonResponse([], safe=False)

    cache_key = brand_children_cache_key(brand_id)
    children = cache.get(cache_key)
    if children is None:
        children = list(
            Brand.objects.filter(parent_id=brand_id).order_by("title").values("id", "title")
        )
        cache.set(cache_key, children, CACHE_TTL)

    return JsonResponse(children, safe=False)


# --------------------------------------------------------------------------
# Reviews
# --------------------------------------------------------------------------
REVIEW_MAX_LENGTH = 2000


def _parse_star(value):
    star = parse_int(value)
    if star is None or not 1 <= star <= 5:
        return None
    return star


@login_required
def add_review(request):
    if request.method != "POST":
        messages.error(request, "Gosmak üçin ýalňyş usul ulanyldy. Siziň bahaňyz goşulmandy.")
        return redirect("/")

    star = _parse_star(request.POST.get("r_rating") or request.POST.get("r_rating-sm"))
    comment = (request.POST.get("r_comment") or request.POST.get("r_comment-sm") or "").strip()

    if star is None:
        messages.error(request, "Baha goýmagyňyzy haýyş edýäris (ýyldyz saýlaň).")
        return redirect(_safe_referer(request))

    Rating.objects.create(
        user=request.user,
        description=comment[:REVIEW_MAX_LENGTH],
        star=star,
        status="pending",
    )
    messages.success(
        request,
        "Siziň bahaňyz üstünlikli goşuldy. Siziň bahaňyz administrator tarapyndan barlanandan soňra görkeziler.",
    )
    return redirect("/")


@login_required
def add_review_product(request):
    back = _safe_referer(request)

    if request.method != "POST":
        messages.error(request, "Gosmak üçin ýalňyş usul ulanyldy. Siziň bahaňyz goşulmandy.")
        return redirect(back)

    star = _parse_star(request.POST.get("rating_star_product"))
    if star is None:
        messages.error(request, "Baha goýmagyňyzy haýyş edýäris (ýyldyz saýlaň).")
        return redirect(back)

    product_id = parse_int(request.POST.get("product_id"))
    product = Product.objects.filter(id=product_id).first() if product_id else None
    if product is None:
        messages.error(request, "Haryt tapylmady.")
        return redirect(back)

    Rating.objects.create(
        user=request.user,
        product=product,
        description=(request.POST.get("comment") or "").strip()[:REVIEW_MAX_LENGTH],
        star=star,
        status="pending",
    )
    messages.success(
        request,
        "Siziň bahaňyz üstünlikli goşuldy. Siziň bahaňyz administrator tarapyndan barlanandan soňra görkeziler.",
    )
    return redirect(back)


def reviews(request):
    ratings = Rating.objects.filter(status="success").select_related("user").order_by("-created_at")
    return render(request, "cart/reviews.html", {"ratings": ratings})
