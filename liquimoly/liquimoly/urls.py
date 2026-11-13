from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

from cart.sitemaps import ProductSitemap, CategorySitemap

sitemaps = {
    "products": ProductSitemap,
    "categories": CategorySitemap,
}

urlpatterns = [
    path('liquimoly-kerim/', admin.site.urls),
    #path('', include('cart.urls')),
    #path('users/', include('users.urls')),
    path("i18n/", include("django.conf.urls.i18n")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path(
        "robots.txt",
        TemplateView.as_view(
            template_name="robots.txt",
            content_type="text/plain",
        ),
    ),
    path('sw.js', TemplateView.as_view(template_name="cart/sw.js", content_type='application/javascript'), name='sw_js'),
]


urlpatterns += i18n_patterns(
    path("", include("cart.urls")),
    path('users/', include('users.urls')),
)


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
