import uuid

from .services import get_place


class DeviceIDMiddleware:
    """Identifies anonymous visitors (device_id cookie) and their region (place_id cookie).

    Sets on every request:
        request.device_id  - str, stable per browser
        request.place      - Place instance or None
        request.place_id   - int or None (only a *valid, existing* place id)
        request.has_place  - bool
    """

    DEVICE_COOKIE = "device_id"
    PLACE_COOKIE = "place_id"

    DEVICE_MAX_AGE = 60 * 60 * 24 * 30 * 3  # 3 months

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        device_id = request.COOKIES.get(self.DEVICE_COOKIE)
        if not device_id or len(device_id) > 64:
            device_id = str(uuid.uuid4())
        request.device_id = device_id

        raw_place = request.COOKIES.get(self.PLACE_COOKIE)
        place = get_place(raw_place) if raw_place else None
        request.place = place
        request.place_id = place.pk if place else None
        request.has_place = place is not None

        response = self.get_response(request)

        if request.COOKIES.get(self.DEVICE_COOKIE) != device_id:
            response.set_cookie(
                key=self.DEVICE_COOKIE,
                value=device_id,
                max_age=self.DEVICE_MAX_AGE,
                httponly=True,
                secure=request.is_secure(),
                samesite="Lax",
            )

        # A cookie pointing to a deleted / garbage place: drop it so the
        # region picker is shown again instead of erroring.
        if raw_place and place is None:
            response.delete_cookie(self.PLACE_COOKIE)

        return response
