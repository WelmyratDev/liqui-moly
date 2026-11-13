"""
Django settings for the Liqui Moly Turkmenistan shop.

All environment-specific values come from environment variables (loaded from
``.env`` next to ``manage.py``).  See ``.env.example`` for the full list.

Production keeps working with the existing ``.env`` unchanged:
    DJANGO_SECRET_KEY, DEBUG, ALLOWED_HOSTS, POSTGRES_* are read as before.
"""
import os
from pathlib import Path

from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DEBUG is off.")

# No more "*" fallback: an unset ALLOWED_HOSTS in production must fail loudly.
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else "")

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    ",".join(f"https://{host}" for host in ALLOWED_HOSTS if host and not host.startswith(".")),
)


# --------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------
INSTALLED_APPS = [
    "jazzmin",

    "django.contrib.admin",
    "django.contrib.sitemaps",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "users",
    "cart",
    "import_export",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "cart.middleware.DeviceIDMiddleware",
]

ROOT_URLCONF = "liquimoly.urls"

SITE_ID = 1

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "cart.context_processors.place_context",
            ],
        },
    },
]

WSGI_APPLICATION = "liquimoly.wsgi.application"


# --------------------------------------------------------------------------
# Database
#   POSTGRES_DB set  -> PostgreSQL (production)
#   otherwise        -> SQLite file (local development)
# --------------------------------------------------------------------------
if os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER"),
            "PASSWORD": os.getenv("POSTGRES_PASS"),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            # Reuse connections between requests instead of reconnecting each time.
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
        }
    }


# --------------------------------------------------------------------------
# Cache
#   The default LocMem cache is per-process: with 3 gunicorn workers every
#   worker had its own copy, so "clear cache" in the admin only cleared one of
#   them.  A file-based cache is shared by all workers on the server and needs
#   no extra service.  Set CACHE_URL=redis://... to use Redis instead.
# --------------------------------------------------------------------------
if os.getenv("CACHE_URL", "").startswith("redis"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.getenv("CACHE_URL"),
            "KEY_PREFIX": "liquimoly",
            "TIMEOUT": 60 * 60,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": os.getenv("CACHE_DIR", str(BASE_DIR / "cache")),
            "TIMEOUT": 60 * 60,
            "OPTIONS": {"MAX_ENTRIES": 5000},
        }
    }


# --------------------------------------------------------------------------
# Admin (jazzmin)
# --------------------------------------------------------------------------
JAZZMIN_SETTINGS = {
    "site_title": "Liqui Moly Admin",
    "site_header": "Liqui Moly",
    "site_brand": "Liqui Moly",
    "site_logo": "logo/liqui-moly.svg",
    "site_logo_classes": "img-circle",
    "welcome_sign": "Welcome to the Liqui Moly Admin Panel",
    "copyright": "Liqui Moly Turkmenistan",
    "search_model": ["users.User", "cart.Product"],
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["users.view_user"]},
        {"name": "Site", "url": "/", "new_window": True},
        {"model": "users.User"},
        {"app": "cart"},
    ],
    "usermenu_links": [
        {"model": "users.User"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": [
        "cart.Order",
        "cart.OrderItem",
        "cart.Product",
        "cart.Category",
        "cart.Banner",
        "cart.Place",
        "users",
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.Group": "fas fa-users",
        "users.User": "fas fa-user-circle",

        "cart.Product": "fas fa-box-open",
        "cart.Order": "fas fa-shopping-bag",
        "cart.OrderItem": "fas fa-shopping-cart",
        "cart.Category": "fas fa-tags",
        "cart.Specification": "fas fa-list-ul",
        "cart.CartItem": "fas fa-cart-plus",
        "cart.Brand": "fas fa-industry",
        "cart.Banner": "fas fa-images",
        "cart.Place": "fas fa-map-marker-alt",
        "cart.Rating": "fas fa-star",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "custom_css": "css/jazzmin.css",
    "custom_js": None,
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {"users.user": "collapsible", "auth.group": "vertical_tabs"},
    "language_chooser": True,
}


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# Login brute-force protection (see users/views.py)
LOGIN_RATE_LIMIT_ATTEMPTS = int(os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS", "10"))
LOGIN_RATE_LIMIT_WINDOW = int(os.getenv("LOGIN_RATE_LIMIT_WINDOW", str(15 * 60)))


# --------------------------------------------------------------------------
# Security (HTTPS-only settings are enabled whenever DEBUG is off)
# --------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# --------------------------------------------------------------------------
# Internationalization
# --------------------------------------------------------------------------
LANGUAGE_CODE = "tk"
TIME_ZONE = "Asia/Ashgabat"
USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [BASE_DIR / "locale"]

LANGUAGES = [
    ("ru", _("Русский")),
    ("en", _("English")),
    ("tk", _("Türkmençe")),
]

MESSAGE_TAGS = {
    messages.INFO: "info",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
    messages.SUCCESS: "success",
}


# --------------------------------------------------------------------------
# Static & media
#   Static files get a content hash in their name (app.3f2a1c.css) so nginx
#   can cache them "forever"; a deploy changes the hash and busts the cache.
#   Requires `python manage.py collectstatic` on every deploy (as before).
# --------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "liquimoly.storage.ForgivingManifestStaticFilesStorage"
        ),
    },
}

# Uploaded product photos are re-encoded into small WebP thumbnails on demand
# (cart/images.py).  Generated files live under MEDIA_ROOT/THUMBNAIL_DIR.
THUMBNAIL_DIR = "thumbs"

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o644

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --------------------------------------------------------------------------
# Logging: everything goes to stderr, which supervisor writes to logs/gunicorn.log
# --------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "cart": {"handlers": ["console"], "level": os.getenv("APP_LOG_LEVEL", "INFO"), "propagate": False},
        "users": {"handlers": ["console"], "level": os.getenv("APP_LOG_LEVEL", "INFO"), "propagate": False},
    },
}
