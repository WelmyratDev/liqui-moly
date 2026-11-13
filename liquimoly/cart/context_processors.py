def place_context(request):
    return {
        "has_place": getattr(request, "has_place", False),
        "place_id": getattr(request, "place_id", None),
    }