import logging
import re
from datetime import timedelta

from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .models import MIN_PASSWORD_LENGTH, User

logger = logging.getLogger(__name__)


def _safe_next(request, default="/"):
    """Only redirect back to our own site (no open redirect to phishing pages)."""
    next_url = request.POST.get("next") or request.GET.get("next") or default
    if url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return default


def _client_ip(request):
    # nginx sets X-Real-IP / X-Forwarded-For; gunicorn itself only sees 127.0.0.1
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "")


def _rate_limit_keys(request, phone):
    digits = re.sub(r"\D", "", phone or "")[-11:] or "-"
    ip = re.sub(r"[^0-9a-fA-F:.]", "", _client_ip(request))[:45] or "-"
    return [f"login_fail:ip:{ip}", f"login_fail:phone:{digits}"]


def _is_rate_limited(keys):
    limit = settings.LOGIN_RATE_LIMIT_ATTEMPTS
    return any((cache.get(key) or 0) >= limit for key in keys)


def _register_failure(keys):
    window = settings.LOGIN_RATE_LIMIT_WINDOW
    for key in keys:
        if cache.add(key, 1, window):
            continue
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, window)


@login_required
def logout_view(request):
    if request.method == "POST":
        next_url = _safe_next(request)
        auth.logout(request)
        messages.success(request, "Siz ulgamdan çykdyňyz.")
        return redirect(next_url)
    return redirect("/")


def login_view(request):
    if request.method != "POST":
        return redirect("/")

    fullname = request.POST.get("fullname")
    phone_number = request.POST.get("phone_number")
    password = request.POST.get("password") or ""
    remember_me = request.POST.get("remember_me") == "on"
    next_url = _safe_next(request)

    keys = _rate_limit_keys(request, (phone_number or "").strip()[:20])
    if _is_rate_limited(keys):
        logger.warning("Login rate limit hit from %s", _client_ip(request))
        messages.error(request, "Gaty köp synanyşyk. Biraz garaşyp, täzeden synanyşyň.")
        return redirect(next_url)

    is_new_account = (
        User.normalize_phone(phone_number) is not None
        and not User.objects.filter(phone_number=User.normalize_phone(phone_number)).exists()
    )
    if is_new_account and len(password) < MIN_PASSWORD_LENGTH:
        messages.error(request, f"Parol azyndan {MIN_PASSWORD_LENGTH} simwoldan ybarat bolmaly.")
        return redirect(next_url)

    user = User.create_user_if_not_exists(request.place, fullname, phone_number, password)

    if user is None:
        _register_failure(keys)
        messages.error(request, "Telefon belgisinde ýalňyşlyk.")
        return redirect(next_url)

    auth_user = auth.authenticate(request, username=user.phone_number, password=password)

    if auth_user is None:
        _register_failure(keys)
        messages.error(request, "Nädogry maglumatlar.")
        return redirect(next_url)

    auth.login(request, auth_user)
    for key in keys:
        cache.delete(key)

    if remember_me:
        request.session.set_expiry(timedelta(days=30))
    else:
        request.session.set_expiry(0)

    messages.success(request, "Siz ulgamyň içine girdiňiz.")
    return redirect(next_url)
