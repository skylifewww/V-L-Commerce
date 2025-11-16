from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cms/", include(wagtailadmin_urls)),
    path("docs/", include(wagtaildocs_urls)),
    path("eshop/", include("eshop.urls", namespace="eshop")),
    path("analytics/", include("analytics.urls", namespace="analytics")),
    path("", include("landing.urls", namespace="landing")),
    path("", include(wagtail_urls)),
]

if settings.DEBUG:
    urlpatterns.insert(0, path("__debug__/", include("debug_toolbar.urls")))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Add cache control headers explicitly
urlpatterns += [
    re_path(r'^static/(?P<path>.*)$', serve, {
        'document_root': settings.STATIC_ROOT,
        'cache_control': f'max-age={settings.STATICFILES_MAX_AGE}, public'
    }),
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
        'cache_control': f'max-age={settings.MEDIA_MAX_AGE}, public'
    }),
]
