import uuid


class DeviceIDMiddleware:
    DEVICE_COOKIE = "device_id"
    PLACE_COOKIE = "place_id"

    DEVICE_MAX_AGE = 60 * 60 * 24 * 30 * 3  # 3

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # device_id
        device_id = request.COOKIES.get(self.DEVICE_COOKIE)

        if not device_id:
            device_id = str(uuid.uuid4())

        request.device_id = device_id

        # place
        place_id = request.COOKIES.get(self.PLACE_COOKIE)

        request.has_place = bool(place_id)
        request.place_id = place_id

        response = self.get_response(request)

        if self.DEVICE_COOKIE not in request.COOKIES:
            response.set_cookie(
                key=self.DEVICE_COOKIE,
                value=device_id,
                max_age=self.DEVICE_MAX_AGE,
                httponly=True,
                secure=True,
                samesite="Lax",
            )

        return response
