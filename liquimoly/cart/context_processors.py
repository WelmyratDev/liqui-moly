from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.functional import SimpleLazyObject
from django.utils.translation import gettext as _

from .services import cart_items_for, cart_total_quantity


def place_context(request):
    """Region + cart info for every template.

    Cart values are lazy: they hit the database only if a template uses them,
    and at most once per request (the navbar shows the count twice).
    """
    cart_product_ids = SimpleLazyObject(
        lambda: sorted(set(cart_items_for(request).values_list("product_id", flat=True)))
    )

    def shop_config():
        # A callable: templates evaluate it only where {{ shop_config }} is used.
        return {
            "hasPlace": bool(getattr(request, "has_place", False)),
            "csrfToken": get_token(request),
            "cartProductIds": list(cart_product_ids),
            "urls": {
                "addToCart": reverse("cart:add-to-cart"),
                "getByBrand": reverse("cart:get-by-brand"),
                "cart": reverse("cart:cart"),
                "setPlace": reverse("cart:set_place"),
                "serviceWorker": reverse("sw_js"),
            },
            "i18n": {
                "added": _("Goşuldy"),
                "chooseModel": _("-- Modeli saýlaň --"),
                "addError": "Täzeden synanyşyň / Ошибка при добавлении в корзину.",
                "map": "Karta",
            },
        }

    return {
        "has_place": getattr(request, "has_place", False),
        "place_id": getattr(request, "place_id", None),
        "current_place": getattr(request, "place", None),
        "cart_count": SimpleLazyObject(lambda: cart_total_quantity(request)),
        "cart_product_ids": cart_product_ids,
        "shop_config": shop_config,
    }
