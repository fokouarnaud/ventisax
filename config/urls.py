from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static
from hub import views
from hub.admin import site
from two_factor.urls import urlpatterns as two_factor_patterns

handler404 = "hub.views.not_found"

urlpatterns = [path("", views.root), path("admin/", site.urls), path("", include(two_factor_patterns))]
for suffix, name, page in [("", "home", "home"), ("presentation/", "about", "about"),
                           ("contact/", "contact", "contact"), ("nouvelles/", "news", "news"),
                           ("secteurs/(?P<slug>[-a-zA-Z0-9_]+)/", "sector", "sector"),
                           ("nouvelles/(?P<slug>[-a-zA-Z0-9_]+)/", "detail", "detail")]:
    urlpatterns.append(re_path(r"^(?P<lang>fr|en)/" + suffix + "$", views.public, {"page": page}, name=name))
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
